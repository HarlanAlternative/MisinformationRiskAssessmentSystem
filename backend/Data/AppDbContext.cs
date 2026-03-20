using Microsoft.EntityFrameworkCore;
using MisinformationRiskAssessment.Api.Models;

namespace MisinformationRiskAssessment.Api.Data;

public sealed class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
{
    public DbSet<AnalysisResult> AnalysisResults => Set<AnalysisResult>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<AnalysisResult>(entity =>
        {
            entity.ToTable("AnalysisResults");
            entity.HasKey(x => x.Id);
            entity.Property(x => x.Title).HasMaxLength(512).IsRequired();
            entity.Property(x => x.Source).HasMaxLength(256);
            entity.Property(x => x.RiskLevel).HasMaxLength(32).IsRequired();
            entity.Property(x => x.Explanation).HasMaxLength(2000).IsRequired();
            entity.Property(x => x.FeatureSignalsJson);
            entity.Property(x => x.CreatedAt).IsRequired();
        });
    }
}
