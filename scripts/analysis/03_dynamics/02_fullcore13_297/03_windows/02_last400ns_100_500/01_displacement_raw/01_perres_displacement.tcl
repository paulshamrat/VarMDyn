# Per-residue C-alpha displacement, aligned through backbone atoms outside
# the measured region. This is the validated stable-core Tcl calculation.
if {[llength $argv] != 10} { error "Usage: topology trajectory equilibrium_structure output_dir start end first_frame last_frame stride output_name" }
lassign $argv topology trajectory equilibrium_structure outdir start end first_frame last_frame stride output_name
if {![file isdirectory $outdir]} { file mkdir $outdir }
set molid [mol new $topology type parm7 waitfor all]
mol addfile $trajectory type netcdf first $first_frame last $last_frame step $stride waitfor all molid $molid
set nframes [molinfo $molid get numframes]
set expected_frames [expr {(($last_frame - $first_frame) / $stride) + 1}]
if {$nframes != $expected_frames} { error "Expected ${expected_frames} frames; found ${nframes}." }
set align_sel "protein and backbone and not (resid ${start} to ${end})"
set reference_molid [mol new $equilibrium_structure type pdb waitfor all]
set reference [atomselect $reference_molid $align_sel frame 0]
set all_atoms [atomselect $molid all]
for {set frame 0} {$frame < $nframes} {incr frame} {
    set mobile [atomselect $molid $align_sel frame $frame]
    set matrix [measure fit $mobile $reference]
    $all_atoms frame $frame; $all_atoms move $matrix; $mobile delete
}
$reference delete
set residues {}
for {set resid $start} {$resid <= $end} {incr resid} {
    set check [atomselect $molid "name CA and resid $resid" frame 0]
    if {[$check num] == 1} { lappend residues $resid }; $check delete
}
if {[llength $residues] != [expr {$end - $start + 1}]} { error "Not all requested C-alpha residues were found for ${start}-${end}." }
array set ref_ca {}
foreach resid $residues { set ref_ca($resid) [atomselect $reference_molid "name CA and resid $resid" frame 0] }
set handle [open [file join $outdir $output_name] w]
set header "frame\ttime_ps"; foreach resid $residues { append header "\t$resid" }; puts $handle $header
for {set frame 0} {$frame < $nframes} {incr frame} {
    set source_frame [expr {$first_frame + ($frame * $stride)}]
    set line "${frame}\t[expr {$source_frame * 100}]"
    foreach resid $residues {
        set current [atomselect $molid "name CA and resid $resid" frame $frame]
        append line "\t[format %.6f [measure rmsd $current $ref_ca($resid)]]"; $current delete
    }
    puts $handle $line
}
close $handle; foreach resid $residues { $ref_ca($resid) delete }
$all_atoms delete; mol delete $molid; mol delete $reference_molid
puts "OK: wrote [file join $outdir $output_name]"; quit
