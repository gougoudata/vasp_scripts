import math, json
from numpy import array
from numpy.linalg import norm
from scipy.optimize import leastsq
from scipy.linalg import eigh
from eigenval2foo import EIGENVAL
import ti3d_eigen

# Get the error corresponding to the params `p` at the specified k-point
# with the given 4-elem list of energy eigenvalues.
def H_err(p, kList, energyList):
    print("intermediate: " + str(p))
    vals = []
    for i in range(len(kList)):
        if norm(kList[i]) > 0.1:
            # ignore large k values
            continue
        vals.append(norm(H_eigen(p, kList[i]) - energyList[i]))
    return vals

# Get the expected 4-band eigenvalues at k-point `k` with params `p`.
def H_eigen(p, k):
    # convert list p to parameter map
    pmap = get_pmap(p)
    # get eigenvals for H_p(k)
    H_p = ti3d_eigen.Hamiltonian_4band(pmap)
    eigenvals, eigenkets = eigh(H_p(rhombRecipToCartesian(k)))
    # convert eigenvals to numpy array
    return array(eigenvals)

# Convert rhombohedral reciprocal lattice units to Cartesian.
# Input k is given in 2pi/a_rhomb units.
# Return (kx, ky, kz) with kx and ky in 2pi/a_hex units and
# kz in 2pi/c_hex units.
def rhombRecipToCartesian(k):
    # convert input to 1/(Angstrom) units
    pi2 = 2.0*math.pi
    a_hex = 4.138
    c_hex = 28.64
    a_rhomb = math.sqrt(a_hex*a_hex/3.0 + c_hex*c_hex/9.0)
    kA = [k[0]*pi2/a_rhomb, k[1]*pi2/a_rhomb, k[2]*pi2/a_rhomb]
    # switch to Cartesian basis
    b1 = array([pi2/a_hex, -pi2/(math.sqrt(3)*a_hex), pi2/c_hex])
    b2 = array([0.0, 2.0*pi2/(math.sqrt(3)*a_hex), pi2/c_hex])
    b3 = array([-pi2/a_hex, -pi2/(math.sqrt(3)*a_hex), pi2/c_hex])
    kC = b1*kA[0] + b2*kA[1] + b3*kA[2]
    # convert output to (2pi/a_hex, 2pi/a_hex, 2pi/c_hex) units
    kC_out = [kC[0]*a_hex/pi2, kC[1]*a_hex/pi2, kC[2]*c_hex/pi2]
    return kC_out

# Convert `p`, a list of parameters, to a map representing these params.
def get_pmap(p):
    pmap = {"C0": p[0], "C1": p[1], "C2": p[2], "M0": p[3], "M1": p[4],
            "M2": p[5], "A0": p[6], "A2": p[7], "B0": p[8], "B2": p[9],
            "R1": p[10], "R2": p[11]}
    return pmap

# Get list of estimated parameter values.
def get_p_est():
    p = None
    with open("4band.json", "r") as propsFile:
        p = json.load(propsFile)
    pe = [p["C0"], p["C1"], p["C2"], p["M0"], p["M1"], p["M2"]]
    pe.extend([p["A0"], -0.5*p["A0"]])
    pe.extend([p["B0"], -0.5*p["B0"]])
    pe.extend([p["R1"], p["R2"]])
    return pe

# Get energies corresponding to the bands in the 4-band model from
# eigenvalue data. Assume these bands are the 2 above and 2 below the
# Fermi energy (verified that this assumption works with band data).
# `points` has eigenval2foo format points[s][b][k]; assume here s=0.
def getEnergyList(points):
    E_F = getFermiEnergy()
    # Find 2 bands above and 2 bands below E_F.
    # Look for when E - E_F changes sign; E_F should be in the gap
    # so we can assume that E - E_F != 0.
    stop_b = 0
    for b in range(len(points[0])):
        E = points[0][b][0]
        if E - E_F > 0.0:
            # when we get here, we have had sign change
            stop_b = b
            break
    bands = [stop_b - 2, stop_b - 1, stop_b, stop_b + 1]
    # assemble list of eigenvalues for 4-band model
    energyList = []
    for k in range(len(points[0][0])):
        energy = []
        for b in bands:
            energy.append(points[0][b][k])
        energyList.append(energy)
    return energyList

# Get Fermi energy from OUTCAR - look for line with "E-fermi".
def getFermiEnergy():
    with open("OUTCAR", "r") as f:
        for line in f:
            if "E-fermi" in line:
                vals = line.strip().split(" ")
                E_F = float(vals[4])
                return E_F
    # if we get here, didn't find E_F
    # TODO - handle this better? sys.exit(1)?
    print("error: E_F not found")
    return 0.0

def main():
    # get eigenvalue data
    e = EIGENVAL("EIGENVAL")
    kList = e.kpoints
    energyList = getEnergyList(e.points)
    # get estimated parameters
    p_est = get_p_est()

    # perform least-squares fit for parameters
    p, ier = leastsq(H_err, p_est, args=(kList, energyList))
    if ier not in [1, 2, 3, 4]:
        # TODO handle error
        print("error in least-squares fit")

    # write output
    print(p)

if __name__ == "__main__":
    main()
