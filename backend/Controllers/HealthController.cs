using Microsoft.AspNetCore.Mvc;
using MisinformationRiskAssessment.Api.Models;
using MisinformationRiskAssessment.Api.Services;

namespace MisinformationRiskAssessment.Api.Controllers;

[ApiController]
[Route("api/health")]
public sealed class HealthController(IHealthService healthService) : ControllerBase
{
    private readonly IHealthService _healthService = healthService;

    [HttpGet]
    public async Task<ActionResult<HealthStatusResponse>> Get(CancellationToken cancellationToken)
    {
        var status = await _healthService.CheckAsync(cancellationToken);
        return Ok(status);
    }
}
