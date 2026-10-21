# %%
"""Polynomial fit of the normalised Rdson versus Tj of the Infineon IQDH29NE2LM5CGSC.

    python fit_rdson.py [--degree 3] [--plot]

Prints the fitted equation Rdson_norm(Tj) = c_n Tj^n + ... + c_0 and the RMSE of
degrees 1 to 5, so the order can be chosen. With --plot the data and the fits are shown.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

# %%
CSV = (
    Path(__file__).parent
    / "data"
    / "Infineon_MOSFET_IQDH29NE2LM5CGSC_Rdson_vs_Tj_data.csv"
)


def fit(tj, rdson, degree):
    """Least-squares polynomial coefficients, highest power first (np.polyval order)."""
    return np.polyfit(tj, rdson, degree)


def rmse(coef, tj, rdson):
    return float(np.sqrt(np.mean((np.polyval(coef, tj) - rdson) ** 2)))


def equation(coef):
    n = len(coef) - 1
    terms = [
        f"{c:+.6g}" + (f"*Tj^{n - i}" if n - i > 1 else "*Tj" if n - i == 1 else "")
        for i, c in enumerate(coef)
    ]
    return "Rdson_norm(Tj) = " + " ".join(terms)


# %%
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--degree", type=int, default=3)
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()

    df = pd.read_csv(CSV)
    tj, rdson = df["Tj"].to_numpy(), df["Rdson_normalized"].to_numpy()

    print(f"{len(tj)} points, Tj {tj.min():.3g} .. {tj.max():.3g}")
    for deg in range(1, 6):
        c = fit(tj, rdson, deg)
        print(f"degree {deg}: RMSE = {rmse(c, tj, rdson):.4g}   {equation(c)}")

    coef = fit(tj, rdson, args.degree)
    print(f"\nSelected (degree {args.degree}):\n{equation(coef)}")
    print("coefficients (highest power first):", np.array2string(coef, precision=8))

    if args.plot:
        import matplotlib.pyplot as plt

        x = np.linspace(tj.min(), tj.max(), 300)
        plt.plot(tj, rdson, "o", label="data")
        plt.plot(x, np.polyval(coef, x), label=f"degree {args.degree}")
        plt.xlabel("Tj")
        plt.ylabel("Rdson normalised")
        plt.grid(True)
        plt.legend()
        plt.show()


# %%
if __name__ == "__main__":
    main()

# %%
