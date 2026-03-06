export function ApplicationLandscape() {
  const actors = ["Field Rep", "Grower"];
  
  const applications = [
    "GX‑Core (Salesforce)",
    "Farmlink/Passport (Custom Applications)",
    "PC&R (Custom Application)",
    "RQI/Farmvisit (Outsystems)",
    "Crop Intelligence",
    "Salesforce"
  ];
  
  const datastores = [
    "Farmlink (Postgresql)",
    "Passport (Postgresql)",
    "Outsystems",
    "Application Database",
    "Ag‑Core",
    "EDP"
  ];

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-8">
      <div>
        <h1>Reference — Application Landscape</h1>
      </div>

      <div className="space-y-8">
        <div>
          <h3 className="mb-4">Actors</h3>
          <div className="space-y-2">
            {actors.map((actor, index) => (
              <div key={index} className="p-4 border border-border rounded-[var(--radius)] bg-card">
                {actor}
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="mb-4">Applications</h3>
          <div className="space-y-2">
            {applications.map((app, index) => (
              <div key={index} className="p-4 border border-border rounded-[var(--radius)] bg-card">
                {app}
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="mb-4">Datastores / Platforms</h3>
          <div className="space-y-2">
            {datastores.map((datastore, index) => (
              <div key={index} className="p-4 border border-border rounded-[var(--radius)] bg-card">
                {datastore}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
