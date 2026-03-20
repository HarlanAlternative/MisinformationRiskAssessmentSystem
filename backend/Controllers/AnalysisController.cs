using Microsoft.AspNetCore.Mvc;
using MisinformationRiskAssessment.Api.Models;
using MisinformationRiskAssessment.Api.Services;

namespace MisinformationRiskAssessment.Api.Controllers;

[ApiController]
[Route("api")]
public sealed class AnalysisController(IAnalysisService analysisService) : ControllerBase
{
    private readonly IAnalysisService _analysisService = analysisService;

    [HttpPost("analyze")]
    public async Task<ActionResult<AnalyzeResponse>> Analyze([FromBody] AnalyzeRequest request, CancellationToken cancellationToken)
    {
        var result = await _analysisService.AnalyzeAsync(request, cancellationToken);
        return Ok(result);
    }

    [HttpGet("history")]
    public async Task<ActionResult<IReadOnlyCollection<HistoryItemResponse>>> GetHistory(CancellationToken cancellationToken)
    {
        var history = await _analysisService.GetHistoryAsync(cancellationToken);
        return Ok(history);
    }

    [HttpGet("result/{id:guid}")]
    public async Task<ActionResult<AnalysisRecordResponse>> GetResult(Guid id, CancellationToken cancellationToken)
    {
        var result = await _analysisService.GetResultAsync(id, cancellationToken);
        return result is null ? NotFound() : Ok(result);
    }
}
