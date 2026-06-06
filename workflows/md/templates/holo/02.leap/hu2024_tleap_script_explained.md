
# Explanation of Hu 2024 ATP·Mg tleap Script

This document explains each part of the tleap script used to build the CDKL5–ATP–Mg system with ff19SB and OPC water using Hu 2024 quantum-derived ATP parameters.

---

## Full Script Explanation

### 1. Custom Atom Types
These atom types are required for the Hu 2024 ATP parameter files. They define different phosphate oxygen hybridizations and water-like oxygen types.
```
addAtomTypes {{"O3" "O" "sp2"}}
addAtomTypes {{"O2" "O" "sp2"}}
addAtomTypes {{"O"  "O" "sp2"}}
addAtomTypes {{"OW" "O" "sp3"}}
addAtomTypes {{"OY" "O" "sp3"}}
```

### 2. Load Force Fields
```
source leaprc.protein.ff19SB
source leaprc.water.opc
```
- Loads ff19SB for protein.
- Loads OPC water model.

### 3. Load OPC-Compatible Ion Parameters
```
loadamberparams frcmod.opc
loadamberparams frcmod.ionslm_126_opc
loadamberparams frcmod.ionslm_1264_opc
```
These parameter sets ensure consistent ion behavior in OPC water.

### 4. Load Hu 2024 ATP Parameters
```
loadAmberPrep   ../ligprep/hu2024/ATP-B3.prepi
loadAmberParams ../ligprep/hu2024/ATP-B3.frcmod
```
These files contain B3LYP-derived charges and bonded parameters for ATP optimized for Mg²⁺ coordination.

### 5. Load Protein, ATP, and Mg²⁺ Coordinates
```
REC = loadpdb ../01.prep/cdl.prot.noH.pdb
LIG = loadpdb ../01.prep/ligand-only-from-complex-atponly.pdb
MG  = loadpdb ../01.prep/mg-only-from-complex-mgonly.pdb
```
- Loads CDKL5 protein.
- Loads ATP ligand extracted from CDK2.
- Loads Mg²⁺ ion from CDK2.

### 6. Combine All Components
```
COM2 = combine { REC LIG MG }
```
Creates a composite system containing protein + ATP + Mg²⁺.

### 7. Charge Check (Unsovlated)
```
charge COM2
```
Displays the total charge before solvation. ATP is −4, Mg is +2.

### 8. Save Gas-Phase System
```
saveamberparm COM2 cdl.hu_atpmg.opc_gas.prmtop cdl.hu_atpmg.opc_gas.inpcrd
```
Writes unsolvated topology for debugging.

### 9. Solvate with OPC Water
```
solvateBox COM2 OPCBOX 14.0
```
Adds an OPC water box with 14 Å buffer.

### 10. Neutralize System
```
# VARMDYN_ION_COMMANDS
```
VarMDyn probes the pre-solvation system charge, then renders this placeholder
as the exact neutralization command required for the current variant, such as
`addIons2 COM2 Na+ 2` or `addIons2 COM2 Cl- 1`. The rendered command and final
ion counts are recorded in `neutralization_plan.txt` and `ion_report.txt`.

### 11. Save Final Solvated System
```
saveamberparm COM2 cdl.hu_atpmg.opc.prmtop cdl.hu_atpmg.opc.inpcrd
```

### 12. Final Charge Check
```
charge COM2
```
Confirms neutrality.

---

## Summary

This script:
- Loads the correct force fields.
- Imports Hu 2024 ATP·Mg quantum parameters.
- Combines protein, ATP, and Mg²⁺.
- Solvates with OPC water.
- Neutralizes the charge.
- Produces ready-to-run AMBER topology and coordinate files.

---

Generated automatically.
