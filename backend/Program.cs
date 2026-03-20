using Microsoft.EntityFrameworkCore;
using MisinformationRiskAssessment.Api.Data;
using MisinformationRiskAssessment.Api.Services;

var builder = WebApplication.CreateBuilder(args);

StartupValidator.Validate(builder.Configuration, builder.Environment.ContentRootPath);

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

builder.Services.Configure<MachineLearningOptions>(builder.Configuration.GetSection("MachineLearning"));
builder.Services.Configure<BertServiceOptions>(builder.Configuration.GetSection("BertService"));

var connectionString = builder.Configuration.GetConnectionString("DefaultConnection");
if (!string.IsNullOrWhiteSpace(connectionString))
{
    builder.Services.AddDbContext<AppDbContext>(options => options.UseSqlServer(connectionString));
}
else
{
    builder.Services.AddDbContext<AppDbContext>(options => options.UseInMemoryDatabase("MisinformationRiskAssessment"));
}

var allowedOrigins = builder.Configuration.GetSection("Cors:AllowedOrigins").Get<string[]>() ?? [];
builder.Services.AddCors(options =>
{
    options.AddPolicy("frontend", policy =>
    {
        if (allowedOrigins.Length == 0)
        {
            policy.AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod();
            return;
        }

        policy
            .WithOrigins(allowedOrigins)
            .AllowAnyHeader()
            .AllowAnyMethod();
    });
});

builder.Services.AddHttpClient<IBertServiceClient, BertServiceClient>();
builder.Services.AddScoped<IFeatureEngineeringService, FeatureEngineeringService>();
builder.Services.AddScoped<IClassicalModelClient, ClassicalModelClient>();
builder.Services.AddScoped<IHybridRiskScoringService, HybridRiskScoringService>();
builder.Services.AddScoped<IAnalysisService, AnalysisService>();
builder.Services.AddScoped<IHealthService, HealthService>();

var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    var dbContext = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    var logger = scope.ServiceProvider.GetRequiredService<ILoggerFactory>().CreateLogger("DatabaseStartup");
    if (dbContext.Database.IsRelational())
    {
        await DatabaseStartup.InitializeAsync(dbContext, logger);
    }
}

app.UseSwagger();
app.UseSwaggerUI();
app.UseCors("frontend");
app.MapControllers();

app.Run();
