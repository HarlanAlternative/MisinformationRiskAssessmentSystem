using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using MisinformationRiskAssessment.Api.Data;
using MisinformationRiskAssessment.Api.Models;

namespace MisinformationRiskAssessment.Api.Services;

public sealed class HealthService(
    AppDbContext dbContext,
    IBertServiceClient bertServiceClient,
    IOptions<MachineLearningOptions> options,
    IWebHostEnvironment environment) : IHealthService
{
    private readonly AppDbContext _dbContext = dbContext;
    private readonly IBertServiceClient _bertServiceClient = bertServiceClient;
    private readonly MachineLearningOptions _options = options.Value;
    private readonly IWebHostEnvironment _environment = environment;

    public async Task<HealthStatusResponse> CheckAsync(CancellationToken cancellationToken)
    {
        var checks = new Dictionary<string, string>();

        if (_dbContext.Database.IsRelational())
        {
            checks["database"] = await _dbContext.Database.CanConnectAsync(cancellationToken) ? "healthy" : "unreachable";
        }
        else
        {
            checks["database"] = "in-memory";
        }

        checks["bertService"] = await _bertServiceClient.IsHealthyAsync(cancellationToken) ? "healthy" : "unreachable";

        var scriptPath = ResolvePath(_options.ClassicalPredictScriptPath);
        var modelDir = ResolvePath(_options.ClassicalModelDirectory);
        checks["classicalScript"] = File.Exists(scriptPath) ? "healthy" : "missing";
        checks["classicalArtifacts"] = Directory.Exists(modelDir) ? "available" : "missing";

        var overall = checks.Values.All(value => value is "healthy" or "available" or "in-memory")
            ? "Healthy"
            : "Degraded";

        return new HealthStatusResponse
        {
            Status = overall,
            Timestamp = DateTime.UtcNow,
            Checks = checks
        };
    }

    private string ResolvePath(string configuredPath)
    {
        if (Path.IsPathRooted(configuredPath))
        {
            return configuredPath;
        }

        return Path.GetFullPath(Path.Combine(_environment.ContentRootPath, configuredPath));
    }
}
