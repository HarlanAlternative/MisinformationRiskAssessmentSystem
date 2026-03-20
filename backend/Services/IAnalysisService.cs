using MisinformationRiskAssessment.Api.Models;

namespace MisinformationRiskAssessment.Api.Services;

public interface IAnalysisService
{
    Task<AnalyzeResponse> AnalyzeAsync(AnalyzeRequest request, CancellationToken cancellationToken);
    Task<IReadOnlyCollection<HistoryItemResponse>> GetHistoryAsync(CancellationToken cancellationToken);
    Task<AnalysisRecordResponse?> GetResultAsync(Guid id, CancellationToken cancellationToken);
}
