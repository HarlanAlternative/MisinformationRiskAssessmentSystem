using System.ComponentModel.DataAnnotations;

namespace MisinformationRiskAssessment.Api.Models;

public sealed class AnalyzeRequest
{
    [Required]
    [MaxLength(512)]
    public string Title { get; set; } = string.Empty;

    public string? Content { get; set; }

    [MaxLength(256)]
    public string? Source { get; set; }
}
