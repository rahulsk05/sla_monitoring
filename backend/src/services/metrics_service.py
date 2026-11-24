
from src.models.overall_metric import OverallMetric
from src.models.service_metric import ServiceMetric
from src.services.overall_metrics_service import OverallMetricsService
from src.services.service_metrics_service import ServiceMetricsService


class MetricsService:
    def __init__(
        self,
        overall_metrics_service: OverallMetricsService,
        service_metrics_service: ServiceMetricsService,
    ) -> None:
        self.overall_metrics_service = overall_metrics_service
        self.service_metrics_service = service_metrics_service

    async def get_dashboard_metrics(
        self,
    ) -> tuple[OverallMetric | None, list[ServiceMetric]]:
        overall_metrics = (
            await self.overall_metrics_service.get_overall_metrics()
        )
        service_metrics = (
            await self.service_metrics_service.get_all_service_metrics()
        )

        return overall_metrics, service_metrics
