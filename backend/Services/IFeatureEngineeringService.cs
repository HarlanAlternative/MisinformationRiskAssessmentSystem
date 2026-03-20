using MisinformationRiskAssessment.Api.Models;

namespace MisinformationRiskAssessment.Api.Services;

public interface IFeatureEngineeringService
{
    FeatureSignals Extract(string title, string? content, string? source);
}
