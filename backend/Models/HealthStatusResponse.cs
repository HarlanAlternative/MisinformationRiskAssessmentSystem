namespace MisinformationRiskAssessment.Api.Models;

public sealed class HealthStatusResponse
{
    public string Status { get; set; } = "Unknown";
    public DateTime Timestamp { get; set; }
    public Dictionary<string, string> Checks { get; set; } = [];
}
