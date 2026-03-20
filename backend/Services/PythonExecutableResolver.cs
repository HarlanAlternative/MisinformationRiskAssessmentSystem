namespace MisinformationRiskAssessment.Api.Services;

public static class PythonExecutableResolver
{
    public static bool TryResolve(string? configuredExecutable, out string resolvedExecutable)
    {
        foreach (var candidate in GetCandidates(configuredExecutable))
        {
            var resolved = ResolvePath(candidate);
            if (!string.IsNullOrWhiteSpace(resolved))
            {
                resolvedExecutable = resolved;
                return true;
            }
        }

        resolvedExecutable = configuredExecutable?.Trim() ?? string.Empty;
        return false;
    }

    public static string ResolveOrThrow(string? configuredExecutable)
    {
        if (TryResolve(configuredExecutable, out var resolvedExecutable))
        {
            return resolvedExecutable;
        }

        throw new InvalidOperationException(
            $"Python executable '{configuredExecutable}' was not found. " +
            "Set MachineLearning__PythonExecutable to a valid interpreter, or leave it unset to allow automatic detection."
        );
    }

    private static IEnumerable<string> GetCandidates(string? configuredExecutable)
    {
        if (!string.IsNullOrWhiteSpace(configuredExecutable))
        {
            yield return configuredExecutable.Trim();
        }

        if (OperatingSystem.IsWindows())
        {
            yield return "python";
            yield return "python3";
            yield return "py";
            yield break;
        }

        yield return "python3";
        yield return "python";
    }

    private static string? ResolvePath(string executable)
    {
        if (string.IsNullOrWhiteSpace(executable))
        {
            return null;
        }

        if (Path.IsPathRooted(executable))
        {
            return File.Exists(executable) ? executable : null;
        }

        if (executable.Contains(Path.DirectorySeparatorChar) || executable.Contains(Path.AltDirectorySeparatorChar))
        {
            var relativePath = Path.GetFullPath(executable);
            return File.Exists(relativePath) ? relativePath : null;
        }

        var pathValue = Environment.GetEnvironmentVariable("PATH");
        if (string.IsNullOrWhiteSpace(pathValue))
        {
            return null;
        }

        var hasExtension = Path.HasExtension(executable);
        var extensions = OperatingSystem.IsWindows()
            ? (Environment.GetEnvironmentVariable("PATHEXT")?.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries) ?? [".exe", ".cmd", ".bat"])
            : [string.Empty];

        foreach (var directory in pathValue.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries))
        {
            var normalizedDirectory = directory.Trim().Trim('"');
            if (string.IsNullOrWhiteSpace(normalizedDirectory))
            {
                continue;
            }

            foreach (var extension in hasExtension ? [string.Empty] : extensions)
            {
                var candidate = Path.Combine(normalizedDirectory, executable + extension);
                if (File.Exists(candidate))
                {
                    return candidate;
                }
            }
        }

        return null;
    }
}
