using System.ComponentModel.DataAnnotations;

namespace MisinformationRiskAssessment.Api.Models;

public sealed class AnalysisResult
{
    [Key]
    public Guid Id { get; set; }

    [Required]
    [MaxLength(512)]
    public string Title { get; set; } = string.Empty;

    public string? Content { get; set; }

    [MaxLength(256)]
    public string? Source { get; set; }

    [Required]
    [MaxLength(32)]
    public string RiskLevel { get; set; } = string.Empty;

    public double ConfidenceScore { get; set; }

    [Required]
    [MaxLength(2000)]
    public string Explanation { get; set; } = string.Empty;

    public string? FeatureSignalsJson { get; set; }

    public DateTime CreatedAt { get; set; }
}
