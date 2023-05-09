
# region imports
from AlgorithmImports import *
# endregion

class wrapper(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2022, 1, 1)
        self.SetEndDate(2023, 1, 1)
        self.SetCash(100000)

     # Create instances of the SymbolData class for different stock pairs
        self.model = [
            meanReversion(self, "AAPL", "MSFT"),
            meanReversion(self, "AAL", "IBM"),
        ]

    def OnData(self, data):
        for model in self.model:
            model.bb.Update(self.Time, model.series.Current.Value)
            model.OnData(data)


class meanReversion:

    def __init__(self, algorithm, tickr1, tickr2):
        self.algorithm = algorithm

        self.ticker_1 = algorithm.AddEquity(tickr1, Resolution.Daily).Symbol
        self.ticker_2 = algorithm.AddEquity(tickr2, Resolution.Daily).Symbol

        # Create two identity indicators (a indicator that repeats the value without any processing)
        self.ticker_1_identity = Identity(tickr1)
        self.ticker_2_identity = Identity(tickr2)

        # Set these indicators to receive the data from ticker_1 and ticker_2
        algorithm.RegisterIndicator(
            self.ticker_1, self.ticker_1_identity, Resolution.Daily)
        algorithm.RegisterIndicator(
            self.ticker_2, self.ticker_2_identity, Resolution.Daily)

        # Create the portfolio as a new indicator using slope of linear regression in research.ipynb
        # Will need to re-compute slope for each pair
        self.series = IndicatorExtensions.Minus(
            self.ticker_1_identity, IndicatorExtensions.Times(self.ticker_2_identity, 0.356))

        # We then create a bollinger band with 120 steps for lookback period
        # Will need to play around with band's std deviation
        self.bb = BollingerBands(120, 0.6, MovingAverageType.Exponential)

        # Define the objectives when going long or going short
        # Can play around with divergent thresholds
        self.long_targets = [PortfolioTarget(
            self.ticker_1, 0.8), PortfolioTarget(self.ticker_2, -0.8)]
        self.short_targets = [PortfolioTarget(
            self.ticker_1, -0.8), PortfolioTarget(self.ticker_2, 0.8)]

        self.is_invested = None

    def OnData(self, data):
        # For daily bars data is delivered at 00:00 of the day containing the closing price of the previous day (23:59:59)
        if (not data.Bars.ContainsKey(self.ticker_1)) or (not data.Bars.ContainsKey(self.ticker_2)):
            return

        # Check if the bolllinger band indicator is ready (filled with 120 steps)
        if not self.bb.IsReady:
            return

        serie = self.series.Current.Value

        self.algorithm.Plot("ticker_2 Prices", "Open",
                            self.algorithm.Securities[self.ticker_2].Open)
        self.algorithm.Plot("ticker_2 Prices", "Close",
                            self.algorithm.Securities[self.ticker_2].Close)

        self.algorithm.Plot("Indicators", "Serie", serie)
        self.algorithm.Plot("Indicators", "Middle",
                            self.bb.MiddleBand.Current.Value)  # moving average
        self.algorithm.Plot("Indicators", "Upper",
                            self.bb.UpperBand.Current.Value)   # upper band
        self.algorithm.Plot("Indicators", "Lower",
                            self.bb.LowerBand.Current.Value)   # lower bank

        # if it is not invested, see if there is an entry point
        if not self.is_invested:
            # if our portfolio is bellow the lower band, enter long
            if serie < self.bb.LowerBand.Current.Value:
                self.algorithm.SetHoldings(self.long_targets)
                self.algorithm.Debug('Entering Long')
                self.is_invested = 'long'

            # if our portfolio is above the upper band, go short
            if serie > self.bb.UpperBand.Current.Value:
                self.algorithm.SetHoldings(self.short_targets)
                self.algorithm.Debug('Entering Short')
                self.is_invested = 'short'

        # if it is invested in something, check the exiting signal (when it crosses the mean)
        elif self.is_invested == 'long':
            if serie > self.bb.MiddleBand.Current.Value:
                self.algorithm.Liquidate()
                self.algorithm.Debug('Exiting Long')
                self.is_invested = None

        elif self.is_invested == 'short':
            if serie < self.bb.MiddleBand.Current.Value:
                self.algorithm.Liquidate()
                self.algorithm.Debug('Exiting Short')
                self.is_invested = None
