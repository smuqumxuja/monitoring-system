from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Callable

from sqlalchemy.orm import Session

from app.models import Alert, EsxiHost, Metric, VirtualMachine
from app.schemas.predictive import PredictiveRiskOut
from app.services.alert_service import resolve_alert, upsert_alert


LOOKBACK_DAYS = 7
FORECAST_DAYS = 7
MIN_SAMPLES = 3
SECONDS_PER_DAY = 86400

LOAD_TARGET_PERCENT = 90.0
VM_RAM_PRESSURE_PERCENT = 90.0
DATASTORE_FREE_TARGET_PERCENT = 0.0

RECOMMEND_RAM = "RAM oshirish"
RECOMMEND_CPU = "CPU limit tekshirish"
RECOMMEND_DATASTORE = "datastore kengaytirish"
RECOMMEND_MIGRATE = "VMni boshqa ESXi hostga ko'chirish"

PREDICTIVE_ALERT_METRICS = {
    "predictive_cpu_growth",
    "predictive_ram_growth",
    "predictive_datastore_full",
    "predictive_vm_ram_pressure",
    "predictive_vm_disk_growth",
}


@dataclass
class Trend:
    current: float
    average: float
    trend_per_day: float
    forecast_7d: float
    sample_count: int
    confidence: float
    days_to_limit: float | None = None


def analyze_predictive_risks(db: Session) -> list[PredictiveRiskOut]:
    since = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    risks: list[PredictiveRiskOut] = []

    hosts = db.query(EsxiHost).filter(EsxiHost.active.is_(True)).order_by(EsxiHost.name.asc()).all()
    for host in hosts:
        metrics = _metrics_for_host(db, host.id, since)
        risks.extend(_host_risks(host, metrics))

    vms = (
        db.query(VirtualMachine)
        .filter(VirtualMachine.monitoring_enabled.is_(True))
        .order_by(VirtualMachine.name.asc())
        .all()
    )
    for vm in vms:
        metrics = _metrics_for_vm(db, vm.id, since)
        risks.extend(_vm_risks(vm, metrics))

    severity = {"critical": 0, "warning": 1}
    return sorted(risks, key=lambda risk: (severity[risk.level], -risk.confidence, risk.source_name, risk.metric))


def sync_predictive_alerts(db: Session) -> list[PredictiveRiskOut]:
    risks = analyze_predictive_risks(db)
    active_keys = {(risk.source_type, risk.source_id, risk.metric) for risk in risks}

    for risk in risks:
        upsert_alert(
            db,
            risk.source_type,
            risk.source_id,
            risk.metric,
            risk.level,
            risk.title,
            f"{risk.message} Tavsiya: {', '.join(risk.recommendations)}.",
        )

    active_alerts = (
        db.query(Alert)
        .filter(Alert.is_active.is_(True), Alert.metric.in_(PREDICTIVE_ALERT_METRICS))
        .all()
    )
    for alert in active_alerts:
        key = (alert.source_type, alert.source_id, alert.metric)
        if key not in active_keys:
            resolve_alert(db, alert.source_type, alert.source_id, alert.metric)

    return risks


def _host_risks(host: EsxiHost, metrics: list[Metric]) -> list[PredictiveRiskOut]:
    risks: list[PredictiveRiskOut] = []
    risks.extend(
        _forecast_load_risk(
            source_type="host",
            source_id=host.id,
            source_name=host.name,
            host_id=host.id,
            host_name=host.name,
            metric_name="predictive_cpu_growth",
            label="CPU",
            points=_points(metrics, lambda item: item.cpu_usage_percent),
            recommendations=[RECOMMEND_CPU, RECOMMEND_MIGRATE],
        )
    )
    risks.extend(
        _forecast_load_risk(
            source_type="host",
            source_id=host.id,
            source_name=host.name,
            host_id=host.id,
            host_name=host.name,
            metric_name="predictive_ram_growth",
            label="RAM",
            points=_points(metrics, lambda item: item.ram_usage_percent),
            recommendations=[RECOMMEND_RAM, RECOMMEND_MIGRATE],
        )
    )
    datastore_risk = _datastore_full_risk(host, metrics)
    if datastore_risk:
        risks.append(datastore_risk)
    return risks


def _vm_risks(vm: VirtualMachine, metrics: list[Metric]) -> list[PredictiveRiskOut]:
    host = vm.host
    host_name = host.name if host else None
    risks: list[PredictiveRiskOut] = []
    risks.extend(
        _forecast_load_risk(
            source_type="vm",
            source_id=vm.id,
            source_name=vm.name,
            host_id=vm.host_id,
            host_name=host_name,
            metric_name="predictive_cpu_growth",
            label="CPU",
            points=_points(metrics, lambda item: item.cpu_usage_percent),
            recommendations=[RECOMMEND_CPU, RECOMMEND_MIGRATE],
        )
    )
    risks.extend(
        _forecast_load_risk(
            source_type="vm",
            source_id=vm.id,
            source_name=vm.name,
            host_id=vm.host_id,
            host_name=host_name,
            metric_name="predictive_vm_disk_growth",
            label="disk",
            points=_points(metrics, lambda item: item.disk_usage_percent),
            recommendations=[RECOMMEND_DATASTORE, RECOMMEND_MIGRATE],
        )
    )
    ram_pressure = _vm_ram_pressure_risk(vm, metrics, host_name)
    if ram_pressure:
        risks.append(ram_pressure)
    return risks


def _forecast_load_risk(
    source_type: str,
    source_id: int,
    source_name: str,
    host_id: int | None,
    host_name: str | None,
    metric_name: str,
    label: str,
    points: list[tuple[datetime, float]],
    recommendations: list[str],
) -> list[PredictiveRiskOut]:
    trend = _trend(points)
    if not trend or trend.trend_per_day <= 0:
        return []

    days_to_limit = _days_to_limit(trend.current, trend.trend_per_day, LOAD_TARGET_PERCENT)
    if trend.forecast_7d < LOAD_TARGET_PERCENT and (days_to_limit is None or days_to_limit > FORECAST_DAYS):
        return []

    trend.days_to_limit = days_to_limit
    level = "critical" if trend.current >= LOAD_TARGET_PERCENT or (days_to_limit is not None and days_to_limit <= 3) else "warning"
    message = (
        f"So'nggi {LOOKBACK_DAYS} kunlik trend bo'yicha {label} usage kuniga "
        f"{trend.trend_per_day:.2f}% o'smoqda. 7 kunlik prognoz: {trend.forecast_7d:.1f}%."
    )
    if days_to_limit is not None:
        message += f" {LOAD_TARGET_PERCENT:.0f}% chegaraga taxminan {days_to_limit:.1f} kunda yetishi mumkin."

    return [
        _risk(
            source_type=source_type,
            source_id=source_id,
            source_name=source_name,
            host_id=host_id,
            host_name=host_name,
            metric=metric_name,
            level=level,
            title=f"{source_name}: {label} yuklama o'sishi",
            message=message,
            recommendations=recommendations,
            trend=trend,
        )
    ]


def _datastore_full_risk(host: EsxiHost, metrics: list[Metric]) -> PredictiveRiskOut | None:
    points = _points(metrics, _datastore_free_percent)
    trend = _trend(points)
    if not trend or trend.trend_per_day >= 0:
        return None

    days_to_full = _days_to_limit(trend.current, trend.trend_per_day, DATASTORE_FREE_TARGET_PERCENT)
    if days_to_full is None or days_to_full > FORECAST_DAYS:
        return None

    trend.days_to_limit = days_to_full
    level = "critical" if days_to_full <= 3 or trend.current <= 5 else "warning"
    message = (
        f"Datastore free space kuniga {abs(trend.trend_per_day):.2f}% kamaymoqda. "
        f"So'nggi qiymat {trend.current:.1f}%, prognoz bo'yicha 7 kun ichida to'lib qolishi mumkin."
    )
    return _risk(
        source_type="host",
        source_id=host.id,
        source_name=host.name,
        host_id=host.id,
        host_name=host.name,
        metric="predictive_datastore_full",
        level=level,
        title=f"{host.name}: datastore to'lish riski",
        message=message,
        recommendations=[RECOMMEND_DATASTORE, RECOMMEND_MIGRATE],
        trend=trend,
    )


def _vm_ram_pressure_risk(vm: VirtualMachine, metrics: list[Metric], host_name: str | None) -> PredictiveRiskOut | None:
    points = _points(metrics, lambda item: item.ram_usage_percent)
    if len(points) < MIN_SAMPLES:
        return None

    values = [value for _, value in points]
    high_count = sum(1 for value in values if value >= VM_RAM_PRESSURE_PERCENT)
    high_ratio = high_count / len(values)
    average = mean(values)
    if high_ratio < 0.8 or average < VM_RAM_PRESSURE_PERCENT:
        return None

    trend = _trend(points) or Trend(
        current=values[-1],
        average=average,
        trend_per_day=0,
        forecast_7d=values[-1],
        sample_count=len(values),
        confidence=min(0.95, 0.6 + high_ratio * 0.3),
    )
    level = "critical" if high_ratio >= 0.95 or trend.current >= 95 else "warning"
    message = (
        f"VM RAM usage so'nggi {LOOKBACK_DAYS} kunda namunalarining {high_ratio * 100:.0f}% qismida "
        f"{VM_RAM_PRESSURE_PERCENT:.0f}% dan yuqori. O'rtacha RAM usage {average:.1f}%."
    )
    return _risk(
        source_type="vm",
        source_id=vm.id,
        source_name=vm.name,
        host_id=vm.host_id,
        host_name=host_name,
        metric="predictive_vm_ram_pressure",
        level=level,
        title=f"{vm.name}: RAM resurs yetishmovchiligi",
        message=message,
        recommendations=[RECOMMEND_RAM, RECOMMEND_MIGRATE],
        trend=trend,
    )


def _risk(
    source_type: str,
    source_id: int,
    source_name: str,
    host_id: int | None,
    host_name: str | None,
    metric: str,
    level: str,
    title: str,
    message: str,
    recommendations: list[str],
    trend: Trend,
) -> PredictiveRiskOut:
    return PredictiveRiskOut(
        id=f"{source_type}-{source_id}-{metric}",
        source_type=source_type,  # type: ignore[arg-type]
        source_id=source_id,
        source_name=source_name,
        host_id=host_id,
        host_name=host_name,
        metric=metric,
        level=level,  # type: ignore[arg-type]
        title=title,
        message=message,
        recommendations=recommendations,
        current_value=round(trend.current, 2),
        average_7d=round(trend.average, 2),
        trend_per_day=round(trend.trend_per_day, 3),
        forecast_7d=round(trend.forecast_7d, 2),
        days_to_limit=round(trend.days_to_limit, 2) if trend.days_to_limit is not None else None,
        sample_count=trend.sample_count,
        confidence=round(trend.confidence, 2),
    )


def _metrics_for_host(db: Session, host_id: int, since: datetime) -> list[Metric]:
    return (
        db.query(Metric)
        .filter(Metric.entity_type == "host", Metric.host_id == host_id, Metric.collected_at >= since)
        .order_by(Metric.collected_at.asc())
        .all()
    )


def _metrics_for_vm(db: Session, vm_id: int, since: datetime) -> list[Metric]:
    return (
        db.query(Metric)
        .filter(Metric.entity_type == "vm", Metric.vm_id == vm_id, Metric.collected_at >= since)
        .order_by(Metric.collected_at.asc())
        .all()
    )


def _points(metrics: list[Metric], value_getter: Callable[[Metric], float | None]) -> list[tuple[datetime, float]]:
    points: list[tuple[datetime, float]] = []
    for metric in metrics:
        value = value_getter(metric)
        if value is None:
            continue
        points.append((_as_utc(metric.collected_at), float(value)))
    return points


def _trend(points: list[tuple[datetime, float]]) -> Trend | None:
    if len(points) < MIN_SAMPLES:
        return None

    start = points[0][0]
    xs = [(_as_utc(timestamp) - start).total_seconds() / SECONDS_PER_DAY for timestamp, _ in points]
    ys = [value for _, value in points]
    x_mean = mean(xs)
    y_mean = mean(ys)
    denom = sum((x - x_mean) ** 2 for x in xs)
    if denom == 0:
        return None

    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denom
    intercept = y_mean - slope * x_mean
    forecast_x = xs[-1] + FORECAST_DAYS
    forecast = intercept + slope * forecast_x
    predicted = [intercept + slope * x for x in xs]
    ss_total = sum((y - y_mean) ** 2 for y in ys)
    ss_residual = sum((y - y_hat) ** 2 for y, y_hat in zip(ys, predicted))
    r_squared = 0.0 if ss_total == 0 else max(0.0, min(1.0, 1 - ss_residual / ss_total))
    confidence = min(0.99, 0.45 + min(len(points), 20) / 40 + r_squared * 0.25)
    return Trend(
        current=ys[-1],
        average=y_mean,
        trend_per_day=slope,
        forecast_7d=forecast,
        sample_count=len(points),
        confidence=confidence,
    )


def _days_to_limit(current: float, trend_per_day: float, limit: float) -> float | None:
    if trend_per_day == 0:
        return None
    days = (limit - current) / trend_per_day
    if days < 0:
        return 0.0
    return days


def _datastore_free_percent(metric: Metric) -> float | None:
    if not metric.datastore_total_bytes:
        return None
    free = metric.datastore_free_bytes or 0
    return free / metric.datastore_total_bytes * 100


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
