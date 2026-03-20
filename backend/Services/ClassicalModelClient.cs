using System.Diagnostics;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Options;
using MisinformationRiskAssessment.Api.Models;

namespace MisinformationRiskAssessment.Api.Services;

public sealed class ClassicalModelClient(
    IOptions<MachineLearningOptions> options,
    IWebHostEnvironment environment,
    ILogger<ClassicalModelClient> logger) : IClassicalModelClient
{
    private readonly MachineLearningOptions _options = options.Value;
    private readonly IWebHostEnvironment _environment = environment;
    private readonly ILogger<ClassicalModelClient> _logger = logger;
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        PropertyNameCaseInsensitive = true
    };

    public async Task<ClassicalPredictionResult> PredictAsync(AnalyzeRequest request, CancellationToken cancellationToken)
    {
        var scriptPath = ResolvePath(_options.ClassicalPredictScriptPath);
        var modelDirectory = ResolvePath(_options.ClassicalModelDirectory);

        if (!File.Exists(scriptPath))
        {
            throw new FileNotFoundException("Classical model prediction script was not found.", scriptPath);
        }

        var startInfo = new ProcessStartInfo
        {
            FileName = PythonExecutableResolver.ResolveOrThrow(_options.PythonExecutable),
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            WorkingDirectory = Path.GetDirectoryName(scriptPath) ?? _environment.ContentRootPath
        };

        startInfo.ArgumentList.Add(scriptPath);
        startInfo.ArgumentList.Add("--model-dir");
        startInfo.ArgumentList.Add(modelDirectory);
        startInfo.Environment["PYTHONUTF8"] = "1";

        using var process = new Process { StartInfo = startInfo };
        if (!process.Start())
        {
            throw new InvalidOperationException("Failed to start the classical model scoring process.");
        }

        var payload = JsonSerializer.Serialize(request, JsonOptions);
        await process.StandardInput.WriteAsync(payload.AsMemory(), cancellationToken);
        await process.StandardInput.FlushAsync();
        process.StandardInput.Close();

        var stdoutTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var stderrTask = process.StandardError.ReadToEndAsync(cancellationToken);

        await process.WaitForExitAsync(cancellationToken);

        var stdout = await stdoutTask;
        var stderr = await stderrTask;

        if (process.ExitCode != 0)
        {
            _logger.LogError("Classical prediction process failed. stderr: {Error}", stderr);
            throw new InvalidOperationException("Classical model scoring failed. Inspect backend logs for details.");
        }

        var result = JsonSerializer.Deserialize<ClassicalPredictionResult>(stdout, JsonOptions);
        if (result is null)
        {
            _logger.LogError("Classical prediction returned invalid JSON. stdout: {Output}", stdout);
            throw new InvalidOperationException("Classical model scoring returned invalid output.");
        }

        return result;
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
