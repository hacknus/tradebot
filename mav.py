import numpy as np


class MAV:
    '''define moving average'''

    def __init__(self, width, num=1):
        self.width = width
        self.num = num
        self.upper_band = [np.nan, np.nan, np.nan]
        self.lower_band = [np.nan, np.nan, np.nan]
        self.mav = [np.nan, np.nan, np.nan]

    def add(self, price=None):
        '''
        computes the moving averages,
        but only the last three entries
        for memory saving purposes
        '''
        if price is None:
            self.upper_band = [np.nan, np.nan, np.nan]
            self.lower_band = [np.nan, np.nan, np.nan]
            self.mav = [np.nan, np.nan, np.nan]
        else:
            self.upper_band = []
            self.lower_band = []
            self.mav = []
            p = [(i[0] + i[1]) / 2. for i in price]
            for y in [p[:-2], p[:-1], p]:
                '''compute average'''
                s = sum(y[-self.width:])
                av = (s / float(self.width))
                s = 0
                '''compute standard deviation'''
                for j in range(1, self.width + 1):
                    s += (y[-j] - av) ** 2
                std = np.sqrt(s / (self.width - 1))
                '''create upper and lower bands'''
                u = av + (std * self.num)
                l = av - (std * self.num)
                self.lower_band.append(l)
                self.upper_band.append(u)
                self.mav.append(av)
