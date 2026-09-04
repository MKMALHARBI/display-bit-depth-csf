#!/usr/bin/env python3
"""
GAMMA_CORRECTION.PY - Hardware gamma LUT (port of the MATLAB/Psychtoolbox code)
===============================================================================
Exact port of MyApproxGammaCorrectionTable.m plus the load/restore block used by
the Stochastic Resonance MATLAB scripts (sr1/sr2/sr3_letter_BrainStimSR_Final.m).

    MATLAB / Psychtoolbox                            Python / GLFW (this module)
    ---------------------------------------------    ---------------------------
    gammapower = 2.2;                                GAMMA_POWER = 2.2
    approxInvGamma = repmat((0:255).^(1/g),3,1)';    make_gamma_table()
    myGammaTableApprox = a / max(a(:));
    save('myGammaTableApprox.mat', ...)              save_gamma_table()
    load myGammaTableApprox                          load_gamma_table()
    old = Screen('ReadNormalizedGammaTable', win);   GammaCorrection.apply()
    Screen('LoadNormalizedGammaTable', win, tbl);      -> glfw.get/set_gamma_ramp
    Screen('LoadNormalizedGammaTable', win, old);    GammaCorrection.restore()

Entry i (i = 0..255) of the table is exactly (i/255)**(1/2.2), the same value in
R, G and B.  It is the inverse of an ASSUMED 2.2 display response: the monitor
raises it back to the power 2.2, so emitted luminance ends up linear in the
value the experiment asked for.  Mid-grey 0.5 leaves the LUT as 0.730.

Like Psychtoolbox's LoadNormalizedGammaTable, this drives the graphics card's
hardware LUT, so it applies to every pixel scanned out on that monitor and is
independent of what the shaders draw.

TWO THINGS TO KNOW, both inherited from the MATLAB code this reproduces:

1. This is an APPROXIMATION, not a measured calibration.  It assumes gamma is
   exactly 2.2 with no black offset.  A photometer-measured table would go in
   the same place - see load_gamma_table() and the *.npy override.

2. The hardware LUT is 256 entries deep, i.e. an 8-bit-shaped curve, while these
   renderers request a 10-bit framebuffer.  The LUT is therefore the coarsest
   stage in the chain.  If measurements later show it eating the 10-bit
   advantage, the alternative is to leave the LUT at identity and apply
   value ** (1/2.2) inside the fragment shaders at full float precision.

Windows note: SetDeviceGammaRamp may silently refuse ramps that deviate far from
linear.  apply() reads the ramp back and warns if it did not take; the registry
key HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\ICM\\GdiIcmGammaRange
= 256 (DWORD) lifts that restriction.  Always check the printed confirmation.

Run standalone to inspect or regenerate the table:
    python lib/gamma_correction.py          # print the table's key values
    python lib/gamma_correction.py --save   # write gamma_table_approx.npy
"""

import os

import numpy as np
import glfw

# --------------------------------------------------------------------------
# The table (MyApproxGammaCorrectionTable.m)
# --------------------------------------------------------------------------

#: MATLAB: gammapower = 2.2
GAMMA_POWER = 2.2

#: Rows in the table.  256 matches the MATLAB (0:255) and the hardware LUT depth.
TABLE_SIZE = 256

#: Optional measured/override table, looked for in the project root and the cwd.
#: Same role as myGammaTableApprox.mat in the MATLAB code.
TABLE_FILENAME = "gamma_table_approx.npy"

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def make_gamma_table(gamma_power=GAMMA_POWER, size=TABLE_SIZE):
    """Build the approximate inverse-gamma table.

    Line-for-line equivalent of MyApproxGammaCorrectionTable.m:

        gammapower = 2.2;
        approxInvGamma = repmat((0:255).^(1/gammapower),3,1)';
        myGammaTableApprox = approxInvGamma/max(approxInvGamma(:));

    Returns an (size, 3) float64 array in 0..1, columns R, G, B (identical).
    """
    approx_inv_gamma = np.tile(
        np.arange(size, dtype=np.float64) ** (1.0 / gamma_power), (3, 1)).T
    return approx_inv_gamma / approx_inv_gamma.max()


def make_identity_table(size=TABLE_SIZE):
    """A do-nothing ramp: entry i is i/(size-1).

    Needed by the luminance measurement tools.  "No gamma correction" is not the
    same as "identity LUT": skipping the load leaves whatever the previous
    program left behind, which on this machine has been an inverse-gamma table
    abandoned by a MATLAB run.  Measuring through that silently corrupts every
    reading, so the tools assert identity rather than assume it.
    """
    return np.tile(np.linspace(0.0, 1.0, size), (3, 1)).T


def ramp_fingerprint(monitor=None):
    """Describe the ramp currently in a monitor's hardware LUT.

    For the measurement CSVs: records what the light actually passed through,
    which the xrandr-derived gamma_r/g/b fields cannot do (they are unset on
    Windows, and never reflected the LUT in any case).
    """
    monitor = monitor or glfw.get_primary_monitor()
    if not monitor:
        return {'lut_state': 'unknown', 'lut_size': 0, 'lut_mid': ''}

    ramp = np.array(glfw.get_gamma_ramp(monitor).red, dtype=np.float64)
    size = ramp.size
    linear = np.linspace(0.0, 1.0, size)
    inverse = np.interp(linear, np.linspace(0.0, 1.0, TABLE_SIZE),
                        make_gamma_table()[:, 0])
    tol = 4.0 / 65535.0
    if np.max(np.abs(ramp - linear)) <= tol:
        state = 'identity'
    elif np.max(np.abs(ramp - inverse)) <= tol:
        state = 'inverse_gamma_%.1f' % GAMMA_POWER
    else:
        state = 'other'
    return {'lut_state': state, 'lut_size': int(size),
            'lut_mid': '%.6f' % ramp[size // 2]}


def save_gamma_table(path=None, gamma_power=GAMMA_POWER, size=TABLE_SIZE):
    """Write the table to disk (MATLAB: save('myGammaTableApprox.mat',...)).

    Only needed to create an override file; the table is otherwise computed at
    run time, so there is nothing that can go missing.
    """
    if path is None:
        path = os.path.join(_PROJECT_ROOT, TABLE_FILENAME)
    table = make_gamma_table(gamma_power, size)
    np.save(path, table)
    return path


def load_gamma_table(path=None):
    """Return the gamma table (MATLAB: load myGammaTableApprox).

    Uses gamma_table_approx.npy from the project root or the cwd if one exists -
    that is where a photometer-measured table would go - and otherwise computes
    the same approximate table the MATLAB code uses.
    """
    candidates = [path] if path else [
        os.path.join(_PROJECT_ROOT, TABLE_FILENAME),
        os.path.join(os.getcwd(), TABLE_FILENAME),
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            table = np.asarray(np.load(candidate), dtype=np.float64)
            if table.ndim == 1:
                table = np.tile(table, (3, 1)).T
            if table.shape[1] != 3:
                raise ValueError(
                    "%s must be (N,3) or (N,), got %s" % (candidate, table.shape))
            return table, candidate
    return make_gamma_table(), None


# --------------------------------------------------------------------------
# Applying it to the monitor
# --------------------------------------------------------------------------

# pyGLFW's NORMALIZE_GAMMA_RAMPS gives us 0..1 ramps (the same convention as
# PTB's "normalized" gamma table), but it converts back with int(), which
# truncates.  Half a step up turns that into round-to-nearest.
_HALF_LSB = 0.5 / 65535.0


class GammaCorrection:
    """Load the inverse-gamma table into a monitor's hardware LUT, and undo it.

    Mirrors the MATLAB block:

        oldGammaTable = Screen('ReadNormalizedGammaTable', winPtr);
        Screen('LoadNormalizedGammaTable', winPtr, myGammaTableApprox);
        ...
        Screen('LoadNormalizedGammaTable', winPtr, oldGammaTable);

    Attributes after apply():
        applied  - the ramp was sent to the driver
        verified - reading it back matched what was sent (trust only this one)
        source   - path of the override table used, or None if computed
    """

    def __init__(self, monitor=None, table=None, verbose=True):
        self._monitor = monitor
        self._old_ramp = None
        self._verbose = verbose
        self.applied = False
        self.verified = False
        if table is None:
            self.table, self.source = load_gamma_table()
        else:
            self.table, self.source = np.asarray(table, dtype=np.float64), None
        # An identity table means "assert no correction", not "correct" - say so
        # in the printout and in the log dict.
        identity = np.linspace(0.0, 1.0, self.table.shape[0])
        self.is_identity = bool(np.allclose(self.table[:, 0], identity, atol=1e-12))
        self.label = "identity" if self.is_identity else "inverse-gamma"

    # -- helpers ---------------------------------------------------------

    def _resampled(self, hw_size):
        """Match the table to the hardware LUT depth.

        The LUT is 256 entries on Windows but can be 1024 or more on Linux.
        Psychtoolbox resamples the 256-row table the same way, so this stays
        faithful to the MATLAB behaviour on whichever OS it runs.
        """
        if hw_size == self.table.shape[0]:
            return self.table
        src = np.linspace(0.0, 1.0, self.table.shape[0])
        dst = np.linspace(0.0, 1.0, hw_size)
        return np.column_stack([np.interp(dst, src, self.table[:, c])
                                for c in range(3)])

    # -- the MATLAB block ------------------------------------------------

    def apply(self):
        """Read and stash the current ramp, then load the corrected one."""
        monitor = self._monitor or glfw.get_primary_monitor()
        if not monitor:
            if self._verbose:
                print("Gamma: no monitor handle - correction NOT applied")
            return False

        self._old_ramp = glfw.get_gamma_ramp(monitor)
        hw_size = len(self._old_ramp.red)
        table = self._resampled(hw_size)

        # Quantise to the 16-bit ramp the driver actually takes, so what we
        # verify against below is what the hardware can hold.
        wanted = np.round(table * 65535.0) / 65535.0
        sent = np.clip(wanted + _HALF_LSB, 0.0, 1.0)
        glfw.set_gamma_ramp(monitor, (sent[:, 0].tolist(),
                                      sent[:, 1].tolist(),
                                      sent[:, 2].tolist()))
        self.applied = True

        # Windows can silently ignore a ramp it dislikes - read it back.
        readback = glfw.get_gamma_ramp(monitor)
        got = np.column_stack([readback.red, readback.green, readback.blue])
        max_err = float(np.max(np.abs(got - wanted))) if got.size else 1.0
        self.verified = max_err <= 2.0 / 65535.0

        if self._verbose:
            src = ("identity" if self.is_identity else
                   self.source if self.source else "computed, gamma=%.2f" % GAMMA_POWER)
            print("Gamma LUT: %d-entry %s table loaded (%s)" %
                  (hw_size, self.label, src))
            if self.verified:
                print("  -> hardware LUT verified (0.5 -> %.3f)" % wanted[hw_size // 2, 0])
            else:
                print("  -> WARNING: LUT readback differs by %.4f - the driver "
                      "rejected or clamped it." % max_err)
                print("     Luminance is NOT linearised. See the Windows "
                      "GdiIcmGammaRange note in lib/gamma_correction.py.")
        return self.verified

    def restore(self):
        """Put the monitor's original ramp back (MATLAB restores oldGammaTable).

        GLFW also restores it on terminate(); doing it explicitly matches the
        MATLAB flow and covers paths where terminate() is never reached.
        """
        if self._old_ramp is None:
            return
        monitor = self._monitor or glfw.get_primary_monitor()
        if monitor:
            glfw.set_gamma_ramp(monitor, (list(self._old_ramp.red),
                                          list(self._old_ramp.green),
                                          list(self._old_ramp.blue)))
        self._old_ramp = None
        self.applied = False

    def info(self):
        """Dict describing what was done, for the experiment's JSON log."""
        return {
            'gamma_correction': ('identity_hardware_lut' if self.is_identity
                                 else 'inverse_gamma_hardware_lut'),
            'gamma_power': 1.0 if self.is_identity else GAMMA_POWER,
            'table_size': int(self.table.shape[0]),
            'table_source': self.source or 'computed',
            'applied': bool(self.applied),
            'verified': bool(self.verified),
        }


# --------------------------------------------------------------------------
# Standalone: inspect or regenerate the table
# --------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if "--save" in sys.argv:
        print("Saved:", save_gamma_table())

    tbl = make_gamma_table()
    print("Table: %s, gamma = %.2f" % (str(tbl.shape), GAMMA_POWER))
    print(" input -> LUT output")
    for i in (0, 32, 64, 128, 192, 255):
        print("  %5.3f -> %5.3f" % (i / 255.0, tbl[i, 0]))
    # Round trip: LUT output raised to 2.2 by the display returns the input.
    err = np.max(np.abs(tbl[:, 0] ** GAMMA_POWER - np.arange(256) / 255.0))
    print("Linearity check (LUT ** 2.2 vs requested): max error %.2e" % err)
