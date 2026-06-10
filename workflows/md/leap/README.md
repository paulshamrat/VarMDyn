# LEaP Helpers

These helpers are called by the apo/holo LEaP shell stages. They are separated
from the top-level MD module because they only handle LEaP neutralization,
output checks, and ion audit reports.

| Script | Role |
|---|---|
| `neutralize.py` | Render charge-aware `addIons2` commands into LEaP inputs. |
| `ion_report.py` | Summarize charge, ion type, and ion counts from LEaP outputs. |
| `check.py` | Verify LEaP products and ion reports for apo/holo systems. |
