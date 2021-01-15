import numpy as np
import matplotlib.pyplot as plt
import pandas as pd


def main():
    df = pd.read_csv("Data/BittrexHistory.csv")
    print(df.head())
    plt.plot(df.Time, df.Close)
    plt.show()


if __name__ == "__main__":
    main()
