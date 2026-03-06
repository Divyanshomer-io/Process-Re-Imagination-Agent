export function StakeholdersOwnership() {
  const coreRoles = [
    "Solution Architect — Ag",
    "I&O Architect — Ag",
    "Enterprise Architect",
    "Data Architect — Ag"
  ];

  const ownershipData = [
    {
      area: "GX‑Core",
      productOwner: "Manpreet",
      engineeringLead: "Gareth",
      solutionArchitect: "Deepak",
      partner: "—"
    },
    {
      area: "Farmlink/Passport",
      productOwner: "Manoj Kumar",
      engineeringLead: "Preeti",
      solutionArchitect: "Deepak",
      partner: "—"
    },
    {
      area: "PC&R",
      productOwner: "Joe/Kevin",
      engineeringLead: "—",
      solutionArchitect: "Deepak",
      partner: "Tech M"
    },
    {
      area: "RQI/Farmvisit",
      productOwner: "—",
      engineeringLead: "—",
      solutionArchitect: "Deepak",
      partner: "NA"
    },
    {
      area: "Crop Intelligence",
      productOwner: "—",
      engineeringLead: "—",
      solutionArchitect: "Deepak",
      partner: "—"
    }
  ];

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-8">
      <div>
        <h1>Reference — Stakeholders & Ownership</h1>
      </div>

      <div className="space-y-8">
        <div>
          <h3 className="mb-4">Core Roles</h3>
          <div className="space-y-2">
            {coreRoles.map((role, index) => (
              <div key={index} className="p-4 border border-border rounded-[var(--radius)] bg-card">
                {role}
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="mb-4">Ownership Grid</h3>
          <div className="border border-border rounded-[var(--radius)] overflow-hidden">
            <table className="w-full">
              <thead className="bg-muted">
                <tr>
                  <th className="text-left px-4 py-3">Area/Application</th>
                  <th className="text-left px-4 py-3">Product Owner</th>
                  <th className="text-left px-4 py-3">Engineering Lead</th>
                  <th className="text-left px-4 py-3">Solution Architect</th>
                  <th className="text-left px-4 py-3">Partner</th>
                </tr>
              </thead>
              <tbody>
                {ownershipData.map((row, index) => (
                  <tr key={index} className="border-t border-border">
                    <td className="px-4 py-3 font-semibold">{row.area}</td>
                    <td className="px-4 py-3">{row.productOwner}</td>
                    <td className="px-4 py-3">{row.engineeringLead}</td>
                    <td className="px-4 py-3">{row.solutionArchitect}</td>
                    <td className="px-4 py-3">{row.partner}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
