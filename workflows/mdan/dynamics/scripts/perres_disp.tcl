# =====================================================================
# VarMDyn per-residue displacement (VMD, NetCDF+parm7)
# Run:     vmd -dispdev text -e workflows/mdan/dynamics/scripts/perres_disp.tcl
# Root assumed = current working directory that contains:
#   <state root>/<variants>/02.leap/com/*.prmtop
#   analysis2/ptraj_subsample/<variant>/04.ptraj/com/cr*/ *.sampled-*.nc
# Outputs go to:
#   analysis2/ptraj_subsample/_perres_disp/<variant>_<replica>/
# =====================================================================

# ---------- Project roots (Palmetto) ----------
set PROJ     [file normalize [pwd]]
set MDROOT   "$PROJ/md"
# ANALYSIS points to the mirror that contains subsampled trajectories
set ANALYSIS "$PROJ/analysis2/ptraj_subsample"

# ---------- Utils ----------
proc ensure_dir {p} { if {![file isdirectory $p]} { file mkdir $p } }

# List variants/replicas from ANALYSIS
proc varmdyn_list {} {
    global ANALYSIS
    puts "Variants under $ANALYSIS:"
    foreach var [lsort [glob -nocomplain -types d "$ANALYSIS/*"]] {
        set v [file tail $var]
        set reps [lsort [glob -nocomplain -types d "$var/04.ptraj/com/cr*"]]
        set repnames {}
        foreach r $reps { lappend repnames [file tail $r] }
        puts "  $v  replicas: [join $repnames , ]"
    }
}

# ---------- Loader (parm7 + netcdf) ----------
# Prefers subsampled NetCDF in analysis2; falls back to originals in MDROOT
# Usage: varmdyn_load WT cr2
proc varmdyn_load {variant replica} {
    global PROJ MDROOT ANALYSIS
    # prmtop (prefer the stripped topology that matches striped trajectories)
    set prmtop_striped "$MDROOT/$variant/02.leap/com/cdl.com.striped_v2.prmtop"
    set prmtop_gas "$MDROOT/$variant/02.leap/com/cdl.com.gas.leap.prmtop"
    set prmtop_wat "$MDROOT/$variant/02.leap/com/cdl.com.wat.leap.prmtop"
    if {[file exists $prmtop_striped]} {
        set prmtop $prmtop_striped
    } elseif {[file exists $prmtop_gas]} {
        set prmtop $prmtop_gas
    } elseif {[file exists $prmtop_wat]} {
        set prmtop $prmtop_wat
    } else {
        error "No prmtop found for $variant (looked for gas/wat in 02.leap/com)"
    }

    # candidates for NetCDF trajectory
    set cand {
        "%ANALYSIS%/%VAR%/04.ptraj/com/%REP%/*.sampled-*.nc"
        "%MDROOT%/%VAR%/04.ptraj/com/%REP%/traj-proc/*.mdcrd.nc"
        "%MDROOT%/%VAR%/04.ptraj/com/%REP%/*.nc"
    }
    set nc ""
    foreach pat $cand {
        set pat [string map [list %ANALYSIS% $ANALYSIS %MDROOT% $MDROOT %VAR% $variant %REP% $replica] $pat]
        set hits [lsort [glob -nocomplain $pat]]
        if {[llength $hits] > 0} { set nc [lindex $hits 0]; break }
    }
    if {$nc eq ""} {
        error "No NetCDF found for $variant/$replica under analysis2 or MDROOT."
    }

    puts "Loading topology (parm7): $prmtop"
    puts "Coordinate source (netcdf): $nc"
    puts "Coordinate/reference policy: trajectory frame 0 supplies coordinates; topology supplies atom definitions."
    set mid [mol new $prmtop type parm7 waitfor all]
    puts "Adding trajectory (netcdf): $nc"
    mol addfile $nc type netcdf waitfor all molid $mid
    puts "Loaded mol $mid: [molinfo $mid get numatoms] atoms; [molinfo $mid get numframes] frames."
    return $mid
}

# ---------- Alignment helper (cached) ----------
if {[info procs varmdyn_align_frames] ne ""} { rename varmdyn_align_frames varmdyn_align_frames__old }
proc varmdyn_align_frames {{align_sel "protein and backbone"} {ref_frame 0}} {
    global VARMDYN_ALIGN_CACHE
    if {![info exists VARMDYN_ALIGN_CACHE]} { array set VARMDYN_ALIGN_CACHE {} }
    set mid [molinfo top]; if {$mid < 0} { error "No molecule loaded." }
    set key "${mid}|${ref_frame}|${align_sel}"
    if {[info exists VARMDYN_ALIGN_CACHE($key)]} { return }
    set nframes [molinfo $mid get numframes]; if {$nframes < 1} { error "Mol $mid has no frames." }
    set ref_sel [atomselect $mid $align_sel frame $ref_frame]
    set sel_all [atomselect $mid "all"]
    puts "▶ Aligning mol $mid to frame $ref_frame using: {$align_sel}"
    for {set i 0} {$i < $nframes} {incr i} {
        set mob [atomselect $mid $align_sel frame $i]
        set M [measure fit $mob $ref_sel]
        $sel_all frame $i; $sel_all move $M
        $mob delete
        if {($i % 200) == 0} { puts "   aligned frame $i / $nframes" }
    }
    $ref_sel delete; $sel_all delete
    set VARMDYN_ALIGN_CACHE($key) 1
    puts "✅ Alignment done."
}

# ---------- Per-residue displacement (WIDE) ----------
# Usage example:
# varmdyn_perres_displacement 19 56 "name CA" 0 1 WT cr2 1 "protein and backbone and not (resid 19 to 56)"
proc varmdyn_perres_displacement {res_start res_end {sel "name CA"} {ref_frame 0} {write_per_frame 1} {variant ""} {replica ""} {do_align 1} {align_sel ""}} {
    set mid [molinfo top]; if {$mid < 0} { error "No molecule loaded." }
    set nframes [molinfo $mid get numframes]; if {$nframes < 1} { error "Mol $mid has no frames." }
    global ANALYSIS

    # infer var/rep if not provided
    if {$variant ne "" && $replica ne ""} {
        set varrep "${variant}_${replica}"
    } else {
        # best-effort from loaded file paths
        set structfile [molinfo $mid get filename]
        if {[regexp {ptraj_subsample/([^/]+)/04\.ptraj/com/(cr[0-9]+)} $structfile -> v r]} {
            set varrep "${v}_${r}"
        } else {
            set varrep "mid${mid}"
        }
    }

    set outroot "$ANALYSIS/_perres_disp"; ensure_dir $outroot
    set outdir  [file join $outroot $varrep]; ensure_dir $outdir

    set sel_tag [string map {" " "" "\"" "" "'" ""} $sel]
    set base "disp_${sel_tag}_res${res_start}-${res_end}.mid${mid}"
    set tsv_wide        [file join $outdir "${base}.tsv"]
    set tsv_perres_mean [file join $outdir "${base}.per_res_mean.tsv"]
    set tsv_perframe    [file join $outdir "${base}.per_frame_mean.tsv"]

    # alignment (exclude ROI)
    if {$do_align} {
        if {$align_sel eq ""} { set align_sel "protein and backbone and not (resid ${res_start} to ${res_end})" }
        varmdyn_align_frames $align_sel $ref_frame
    } else {
        puts "▶ Align OFF (do_align=0) | ref=$ref_frame"
    }

    # residue list present in selection
    set res_list {}
    for {set r $res_start} {$r <= $res_end} {incr r} {
        set chk [atomselect $mid "$sel and resid $r" frame $ref_frame]
        if {[$chk num] > 0} { lappend res_list $r }
        $chk delete
    }
    if {[llength $res_list] == 0} {
        error "No atoms matched '$sel' in resid ${res_start}-${res_end} at ref frame $ref_frame."
    }

    # reference selections
    array unset REF
    foreach r $res_list { set REF($r) [atomselect $mid "$sel and resid $r" frame $ref_frame] }

    # write wide matrix
    set fh [open $tsv_wide w]
    set header "frame"; foreach r $res_list { append header "\t$r" }; puts $fh $header

    array set sum_per_res {}; foreach r $res_list { set sum_per_res($r) 0.0 }
    set per_frame_means {}

    puts "▶ Computing displacement matrix (frames 0..[expr {$nframes-1}], sel={$sel})"
    for {set i 0} {$i < $nframes} {incr i} {
        set line "$i"; set frame_sum 0.0; set cnt 0
        foreach r $res_list {
            set mob [atomselect $mid "$sel and resid $r" frame $i]
            set d "NaN"
            if {[$mob num] == [$REF($r) num] && [$mob num] > 0} {
                set d [measure rmsd $mob $REF($r)]
                set sum_per_res($r) [expr {$sum_per_res($r) + $d}]
                set frame_sum [expr {$frame_sum + $d}]
                incr cnt
            }
            $mob delete
            append line "\t[format %.6f $d]"
        }
        puts $fh $line
        if {$write_per_frame && $cnt > 0} {
            lappend per_frame_means [expr {$frame_sum / double($cnt)}]
        }
        if {($i % 200) == 0} { puts "  processed frame $i / $nframes" }
    }
    close $fh

    # per-res means
    set fh2 [open $tsv_perres_mean w]; puts $fh2 "resid\tmean_displacement_A"
    foreach r $res_list {
        puts $fh2 "$r\t[format %.6f [expr {$sum_per_res($r) / double($nframes)}]]"
    }
    close $fh2

    # per-frame mean
    if {$write_per_frame} {
        set fh3 [open $tsv_perframe w]; puts $fh3 "frame\tmean_over_residues_A"
        for {set i 0} {$i < [llength $per_frame_means]} {incr i} {
            puts $fh3 "$i\t[format %.6f [lindex $per_frame_means $i]]"
        }
        close $fh3
    }

    foreach r $res_list { $REF($r) delete }
    puts "✅ Wrote: $tsv_wide"
    puts "✅ Wrote: $tsv_perres_mean"
    if {$write_per_frame} { puts "✅ Wrote: $tsv_perframe" }
    return $tsv_wide
}

# ============================== PARAMETERS ===============================
# --- tweak these if needed ---
set RES_START       19
set RES_END         56
set SEL             "name CA"
set REF_FRAME       0
set WRITE_PER_FRAME 1
set DO_ALIGN        1
set ALIGN_SEL       "protein and backbone and not (resid ${RES_START} to ${RES_END})"
# ========================================================================

# Summary
puts "PROJ    = $PROJ"
puts "MDROOT  = $MDROOT"
puts "ANALYSIS= $ANALYSIS"
puts "Coordinate/reference policy: NetCDF trajectory frame $REF_FRAME is the alignment and displacement reference."
puts "ALIGN_SEL = $ALIGN_SEL"
varmdyn_list
puts "------------------------------------------------------------------"

# Discover jobs from analysis2/ptraj_subsample
set JOBS {}
foreach varDir [lsort [glob -nocomplain -types d "$ANALYSIS/*"]] {
    set variant [file tail $varDir]
    foreach repDir [lsort [glob -nocomplain -types d "$varDir/04.ptraj/com/cr*"]] {
        set replica [file tail $repDir]
        lappend JOBS [list $variant $replica]
    }
}
if {[llength $JOBS] == 0} {
    puts "No jobs found under: $ANALYSIS  (expected * /04.ptraj/com/cr*)"
    return
} else {
    puts "Found [llength $JOBS] jobs:"; foreach job $JOBS { puts "  [lindex $job 0]  [lindex $job 1]" }
    puts "------------------------------------------------------------------"
}

# Run all jobs
set nOK 0; set nERR 0
foreach job $JOBS {
    lassign $job variant replica
    puts "=================================================================="
    puts "[clock format [clock seconds] -format {%Y-%m-%d %H:%M:%S}] ▶ $variant $replica"
    catch { mol delete all }
    if {[catch {
        varmdyn_load $variant $replica
        varmdyn_perres_displacement $RES_START $RES_END $SEL $REF_FRAME $WRITE_PER_FRAME \
            $variant $replica $DO_ALIGN $ALIGN_SEL
        mol delete top
    } msg]} {
        incr nERR
        puts "❌ ERROR: $variant $replica :: $msg"
        catch { mol delete all }
    } else {
        incr nOK
        puts "✅ DONE:  $variant $replica"
    }
}
puts "------------------------------------------------------------------"
puts "All jobs finished. Success: $nOK   Errors: $nERR"
puts "Outputs: $ANALYSIS/_perres_disp/<variant>_<replica>/"
# =====================================================================
