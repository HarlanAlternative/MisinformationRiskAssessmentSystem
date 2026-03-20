using MisinformationRiskAssessment.Api.Models;

namespace MisinformationRiskAssessment.Api.Services;

public interface IHealthService
{
    Task<HealthStatusResponse> CheckAsync(CancellationToken cancellationToken);
}
