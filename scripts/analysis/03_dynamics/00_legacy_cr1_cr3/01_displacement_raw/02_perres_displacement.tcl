# Per-residue C-alpha displacement for one trajectory and one residue window.
# Called only by 01_extract_displacement.sbatch:
#   vmd -dispdev text -e 02_perres_displacement.tcl \
#       -args topology.prmtop trajectory.nc output_dir start end stride output_name
#
# VMD loads every `stride` trajectory frame. Each loaded frame is fitted to
# frame 0 using backbone atoms outside the measured residue window. The output
# is a wide TSV: one row per sampled frame and one column per measured residue.

if {[llength $argv] != 7} {
    error "Usage: topology trajectory output_dir start end stride output_name"
}
lassign $argv topology trajectory outdir start end stride output_name

proc ensure_dir {path} {
    if {![file isdirectory $path]} { file mkdir $path }
}

ensure_dir $outdir
set molid [mol new $topology type parm7 waitfor all]
mol addfile $trajectory type netcdf first 0 step $stride waitfor all molid $molid
set nframes [molinfo $molid get numframes]
if {$nframes != 1250} {
    error "Expected 1,250 frames after stride ${stride}; found ${nframes}."
}

set align_sel "protein and backbone and not (resid ${start} to ${end})"
set reference [atomselect $molid $align_sel frame 0]
set all_atoms [atomselect $molid all]

# Align every sampled frame to the first sampled frame without fitting the ROI.
for {set frame 0} {$frame < $nframes} {incr frame} {
    set mobile [atomselect $molid $align_sel frame $frame]
    set matrix [measure fit $mobile $reference]
    $all_atoms frame $frame
    $all_atoms move $matrix
    $mobile delete
}
$reference delete

set residues {}
for {set resid $start} {$resid <= $end} {incr resid} {
    set check [atomselect $molid "name CA and resid $resid" frame 0]
    if {[$check num] == 1} { lappend residues $resid }
    $check delete
}
if {[llength $residues] != [expr {$end - $start + 1}]} {
    error "Not all requested C-alpha residues were found for ${start}-${end}."
}

array set ref_ca {}
foreach resid $residues {
    set ref_ca($resid) [atomselect $molid "name CA and resid $resid" frame 0]
}

set outfile [file join $outdir $output_name]
set handle [open $outfile w]
set header "frame\ttime_ps"
foreach resid $residues { append header "\t$resid" }
puts $handle $header

for {set frame 0} {$frame < $nframes} {incr frame} {
    set line "${frame}\t[expr {$frame * 400}]"
    foreach resid $residues {
        set current [atomselect $molid "name CA and resid $resid" frame $frame]
        set distance [measure rmsd $current $ref_ca($resid)]
        append line "\t[format %.6f $distance]"
        $current delete
    }
    puts $handle $line
}
close $handle

foreach resid $residues { $ref_ca($resid) delete }
$all_atoms delete
mol delete $molid
puts "OK: wrote ${outfile}"
quit
