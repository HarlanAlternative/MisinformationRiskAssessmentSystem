using MisinformationRiskAssessment.Api.Models;

namespace MisinformationRiskAssessment.Api.Services;

public interface IClassicalModelClient
{
    Task<ClassicalPredictionResult> PredictAsync(AnalyzeRequest request, CancellationToken cancellationToken);
}
