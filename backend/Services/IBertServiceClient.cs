using MisinformationRiskAssessment.Api.Models;

namespace MisinformationRiskAssessment.Api.Services;

public interface IBertServiceClient
{
    Task<BertPredictionResult> PredictAsync(AnalyzeRequest request, CancellationToken cancellationToken);
    Task<bool> IsHealthyAsync(CancellationToken cancellationToken);
}
