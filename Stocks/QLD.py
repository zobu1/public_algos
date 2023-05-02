# region imports
from AlgorithmImports import *
from collections import deque
import numpy as np
# endregion

class CumulativeReturn(PythonIndicator):
    """
    Returns the cumulative return (the difference between
    the first and last data points of the period divided
    by the first data point) as a percentage.
    """
    def __init__(self, period):
        self.WarmUpPeriod = period
        self.Value = 0
        self.queue = deque(maxlen=period)

    def Update(self, input) -> bool:
        self.queue.appendleft(input)
        count = len(self.queue)
        self.Value = (self.queue[-1] - self.queue[0]) / self.queue[0] * 100
        return count == self.queue.maxlen

class CustomStandardDeviation(PythonIndicator):
    def __init__(self, period):
        self.Value = 0
        self.queue = deque(maxlen=period)
    def Update(self, input) -> bool:
        self.queue.appendleft(input)
        count = len(self.queue)
        self.Value = np.std(self.queue)
        return count == self.queue.maxlen


class UpgradedVioletCobra(QCAlgorithm):

    # Todo: Export this function to a library
    def getIndicatorType(self, indicator: str):
        switcher = {
            'SMA': SimpleMovingAverage,
            'RSI': RelativeStrengthIndex,
            'CR': CumulativeReturn,
            'STD': CustomStandardDeviation,
        }
        return switcher.get(indicator)

    def Initialize(self):
        self.SetStartDate(2007, 1, 1)  # Set Start Date
        self.SetCash(10000)  # Set Strategy Cash

        self.equities = tuple()
        self.indicators = dict()

        self.all_indicators = {
            'SMA': {'SPY': (200,), 'QLD': (20,)},
            'RSI': 
                {'QLD': (10,5), 'SPXL': (10,), 'PSQ': (5,10), 
                'SOXS': (5,), 'TLT': (5,), 'SOXL': (5,), 'SPY': (10,), 
                'UVXY': (10,), 'QQQ': (10,)},
            'CR': {'QQQ': (5,), 'TQQQ': (1,)},
            'STD': {'QQQ': (10,)},
        }

        # Instantiate indicators
        for indicator in self.all_indicators:
            for equity, periods in self.all_indicators[indicator].items():
                if not equity in self.equities:
                    self.AddEquity(equity, Resolution.Daily)
                    self.equities += (equity,)
                    self.indicators[equity] = dict()
                self.indicators[equity][indicator] = dict()
                for period in periods:
                    indicator_type = self.getIndicatorType(indicator)
                    self.indicators[equity][indicator][f'Period-{period}'] = indicator_type(period)

        self.Schedule.On(self.DateRules.EveryDay("SPY"),
                            self.TimeRules.BeforeMarketClose("SPY", 2),
                            self.FunctionBeforeMarketClose)

    def OnData(self, data: Slice):
        pass
    
    def warmUpIndicators(self):
        for indicator in self.all_indicators:
            for equity, periods in self.all_indicators[indicator].items():
                for period in periods:
                    selected_indicator = self.indicators[equity][indicator][f'Period-{period}']
                    if not selected_indicator.IsReady:
                        history = self.History(equity, period, Resolution.Daily)
                        for bar in history:
                            if not indicator == 'STD' and not indicator == 'CR':
                                selected_indicator.Update(bar.EndTime, bar.Close)
                            elif indicator == 'STD':
                                selected_indicator.Update((bar.Close - bar.Open) / bar.Open * 100)
                            else:
                                selected_indicator.Update(bar.Close)
                    elif not indicator == 'STD' and not indicator == 'CR':
                        selected_indicator.Update(self.Time, self.Securities[equity].Close)
                    elif indicator == 'STD':
                        selected_indicator.Update((self.Securities[equity].Close - self.Securities[equity].Open) / self.Securities[equity].Open * 100)
                    else:
                        selected_indicator.Update(self.Securities[equity].Close)



    def sortEquitiesByIndicator(self, equities: list, indicator: str, period: int, reverse=False):
        def getCurrentIndicatorValue(equity: str):
            return self.indicators[equity][indicator][f'Period-{period}'].Current.Value
        return sorted(equities, key=getCurrentIndicatorValue, reverse=reverse)

    def TLT(self , asset):
        if asset == 'TLT':
            self.Liquidate()
        else:
            self.SetHoldings(asset, 1, True)


    def FunctionBeforeMarketClose(self):
        self.warmUpIndicators()
        # Algorithm logic
        if self.Securities['SPY'].Close > self.indicators['SPY']['SMA']['Period-200'].Current.Value:
            if self.indicators['QQQ']['RSI']['Period-10'].Current.Value > 80:
                self.SetHoldings('PSQ', 1, True)
            else:
                if self.indicators['SPY']['RSI']['Period-10'].Current.Value > 80:
                    self.SetHoldings('SH', 1, True)
                else:
                    if self.indicators['QQQ']['STD']['Period-10'].Current.Value > 2:
                        self.Liquidate()
                    else:
                        self.SetHoldings('QLD', 1, True)
                        
        else:
            if self.indicators['QQQ']['RSI']['Period-10'].Current.Value < 30:
                self.SetHoldings('QLD', 1, True)
            else:
                if self.indicators['SPY']['RSI']['Period-10'].Current.Value < 30:
                    self.SetHoldings('QLD', 1, True)
                else:
                    if self.Securities['QLD'].Close > self.indicators['QLD']['SMA']['Period-20'].Current.Value:
                         if self.indicators['PSQ']['RSI']['Period-10'].Current.Value < 31:
                            asset = self.sortEquitiesByIndicator(['PSQ',  'TLT'], 'RSI', 5, reverse=True)[-1]
                            self.TLT(asset)
                         else:
                            self.SetHoldings('QLD' , 1, True)
                    else:
                        asset = self.sortEquitiesByIndicator(['PSQ', 'TLT'], 'RSI', 5)[-1]
                        self.TLT(asset)
                        
