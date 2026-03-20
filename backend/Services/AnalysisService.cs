using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using MisinformationRiskAssessment.Api.Data;
using MisinformationRiskAssessment.Api.Models;

namespace MisinformationRiskAssessment.Api.Services;

public sealed class AnalysisService(
    AppDbContext dbContext,
    IFeatureEngineeringService featureEngineeringService,
    IClassicalModelClient classicalModelClient,
    IBertServiceClient bertServiceClient,
    IHybridRiskScoringService hybridRiskScoringService,
    ILogger<AnalysisService> logger) : IAnalysisService
{
    private readonly AppDbContext _dbContext = dbContext;
    private readonly IFeatureEngineeringService _featureEngineeringService = featureEngineeringService;
    private readonly IClassicalModelClient _classicalModelClient = classicalModelClient;
    private readonly IBertServiceClient _bertServiceClient = bertServiceClient;
    private readonly IHybridRiskScoringService _hybridRiskScoringService = hybridRiskScoringService;
    private readonly ILogger<AnalysisService> _logger = logger;

    public async Task<AnalyzeResponse> AnalyzeAsync(AnalyzeRequest request, CancellationToken cancellationToken)
    {
        var featureSignals = _featureEngineeringService.Extract(request.Title, request.Content, request.Source);
        var classicalPrediction = await _classicalModelClient.PredictAsync(request, cancellationToken);
        var bertPrediction = await _bertServiceClient.PredictAsync(request, cancellationToken);
        var riskAssessment = _hybridRiskScoringService.Evaluate(request, featureSignals, classicalPrediction, bertPrediction);

        featureSignals.ModelScores = riskAssessment.ModelScores;
        featureSignals.TopKeywords = riskAssessment.TopKeywords;
        featureSignals.TransformerTokens = riskAssessment.TransformerTokens;

        var result = new AnalysisResult
        {
            Id = Guid.NewGuid(),
            Title = request.Title,
            Content = request.Content,
            Source = request.Source,
            RiskLevel = riskAssessment.RiskLevel,
            ConfidenceScore = riskAssessment.ConfidenceScore,
            Explanation = riskAssessment.Explanation,
            FeatureSignalsJson = JsonSerializer.Serialize(featureSignals),
            CreatedAt = DateTime.UtcNow
        };

        try
        {
            _dbContext.AnalysisResults.Add(result);
            await _dbContext.SaveChangesAsync(cancellationToken);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to persist analysis result {ResultId}. Returning inference response without history persistence.", result.Id);
        }

        return new AnalyzeResponse
        {
            Id = result.Id,
            RiskLevel = result.RiskLevel,
            ConfidenceScore = result.ConfidenceScore,
            Explanation = result.Explanation,
            FeatureSignals = featureSignals,
            CreatedAt = result.CreatedAt
        };
    }

    public async Task<IReadOnlyCollection<HistoryItemResponse>> GetHistoryAsync(CancellationToken cancellationToken)
    {
        try
        {
            return await _dbContext.AnalysisResults
                .AsNoTracking()
                .OrderByDescending(item => item.CreatedAt)
                .Take(50)
                .Select(item => new HistoryItemResponse
                {
                    Id = item.Id,
                    Title = item.Title,
                    RiskLevel = item.RiskLevel,
                    ConfidenceScore = item.ConfidenceScore,
                    Explanation = item.Explanation,
                    CreatedAt = item.CreatedAt
                })
                .ToListAsync(cancellationToken);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to load analysis history. Returning an empty collection.");
            return [];
        }
    }

    public async Task<AnalysisRecordResponse?> GetResultAsync(Guid id, CancellationToken cancellationToken)
    {
        AnalysisResult? item;
        try
        {
            item = await _dbContext.AnalysisResults
                .AsNoTracking()
                .FirstOrDefaultAsync(result => result.Id == id, cancellationToken);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to load analysis result {ResultId}. Returning null.", id);
            return null;
        }

        if (item is null)
        {
            return null;
        }

        var featureSignals = string.IsNullOrWhiteSpace(item.FeatureSignalsJson)
            ? _featureEngineeringService.Extract(item.Title, item.Content, item.Source)
            : JsonSerializer.Deserialize<FeatureSignals>(item.FeatureSignalsJson) ?? _featureEngineeringService.Extract(item.Title, item.Content, item.Source);

        return new AnalysisRecordResponse
        {
            Id = item.Id,
            Title = item.Title,
            Content = item.Content,
            Source = item.Source,
            RiskLevel = item.RiskLevel,
            ConfidenceScore = item.ConfidenceScore,
            Explanation = item.Explanation,
            FeatureSignals = featureSignals,
            CreatedAt = item.CreatedAt
        };
    }
}
