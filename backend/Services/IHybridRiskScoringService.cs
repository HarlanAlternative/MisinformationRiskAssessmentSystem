using MisinformationRiskAssessment.Api.Models;

namespace MisinformationRiskAssessment.Api.Services;

public interface IHybridRiskScoringService
{
    RiskAssessment Evaluate(
        AnalyzeRequest request,
        FeatureSignals featureSignals,
        ClassicalPredictionResult classicalPrediction,
        BertPredictionResult bertPrediction);
}
