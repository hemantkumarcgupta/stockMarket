# -*- coding: utf-8 -*-
"""
Created on Sat Feb  3 14:30:00 2024

@author: Hemant
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def yfDownload(tickerName, period, interval):
    yfTicker = yf.Ticker(tickerName)
    df = yfTicker.history(period=period).dropna().reset_index()
    df = yfDownloadProcessing(df)
    dfInterval = yfTicker.history(period='1mo', interval=interval).dropna().reset_index()
    dfInterval = yfDownloadProcessingInterval(df, dfInterval)
    return df, dfInterval

def yfDownloadProcessing(df):
    df['Date'] = pd.to_datetime(df['Date'])
    df['Day'] = df['Date'].dt.day_name()
    df['Date'] = df['Date'].dt.date
    df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']].round(2)
    df['PvClose'] = df['Close'].shift(1)
    df = df.dropna().reset_index(drop=True)
    df = df[['Date', 'Open', 'High', 'Low', 'Close', 'PvClose', 'Volume', 'Day']]
    return df

def yfDownloadProcessingInterval(dfDay, df):
    df['Date'] = df['Datetime'].dt.date
    df['Datetime'] = pd.to_datetime(df['Datetime'])
    df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']].round(2)
    df = pd.merge(df, dfDay[['Date', 'Open']].rename(columns={'Open': 'OpenDay'}), how='left', on='Date')
    df['CandleP/N_OpenDay'] = df.apply(lambda row: 1 if row['OpenDay'] <= row['Open'] else -1, axis=1)
    df['CandleP/N'] = df.apply(lambda row: 1 if row['Open'] <= row['Close'] else -1, axis=1)
    df = df[['Date', 'Datetime', 'Open', 'High', 'Low', 'Close', 'OpenDay', 'CandleP/N_OpenDay', 'CandleP/N']]
    return df

def formulaPercentage(df):
    df['P/L'] = ((1-df['Open']/df['Close'])*100).round(2)    
    df['maxHigh'] = ((1-df['Open']/df['High'])*100).round(2)
    df['maxLow'] = ((1-df['Open']/df['Low'])*100).round(2)
    df['DiffPvClose/Open'] = (df['Open']-df['PvClose']).round(2)  
    df['closeTolerance'] = df.apply(lambda row: row['P/L'] - row['maxHigh'] if row['P/L'] > 0 else row['P/L'] - row['maxLow'] if row['P/L'] < 0 else 0, axis=1)
    df['priceBand'] = (((df['High'] - df['Low'])/df['Open'])*100).round(2)
    return df

def EntryExitMinToMax(dfInterval):
    dfEtEx = dfInterval.groupby('Date')['Low'].min().reset_index()
    dfEtEx = pd.merge(dfEtEx, dfInterval[['Date', 'Low', 'Datetime']], how='left', on=['Date', 'Low']).drop_duplicates(subset=['Date', 'Low'], keep='last').reset_index(drop=True).rename(columns={'Low': 'Entry', 'Datetime': 'entryDatetime'})
    dfEtEx[['Exit', 'exitDatetime']] = dfEtEx.apply(lambda row: dfInterval.loc[dfInterval[(dfInterval['Date'] == row['Date']) & (dfInterval['Datetime'] >= row['entryDatetime'])]['High'].idxmax(), ['High', 'Datetime']], axis=1)
    dfEtEx = pd.merge(dfEtEx, dfInterval[['Date', 'Datetime', 'OpenDay']].drop_duplicates(subset='Date', keep='first').reset_index(drop=True).rename(columns={'Datetime': 'OpenDayDatetime'}), how='left', on='Date')
    dfEtEx = dfEtEx[['Date', 'OpenDayDatetime', 'entryDatetime', 'exitDatetime', 'OpenDay', 'Entry','Exit']]
    dfEtEx['entrytimeDiff'] = ((dfEtEx['entryDatetime'] - dfEtEx['OpenDayDatetime']).dt.total_seconds()/60).astype(int)
    dfEtEx['exittimeDiff'] = ((dfEtEx['exitDatetime'] - dfEtEx['entryDatetime']).dt.total_seconds()/60).astype(int)
    dfEtEx['OpenToEntryLoss'] = ((1-dfEtEx['OpenDay']/dfEtEx['Entry'])*100).round(2)
    dfEtEx['OpenToExitProfit'] = ((1-dfEtEx['OpenDay']/dfEtEx['Exit'])*100).round(2)
    dfEtEx['EtExProfit'] = ((1-dfEtEx['Entry']/dfEtEx['Exit'])*100).round(2)
    dfEtEx = dfEtEx[['Date', 'Entry', 'Exit', 'entrytimeDiff', 'exittimeDiff', 'OpenToEntryLoss', 'OpenToExitProfit', 'EtExProfit']].rename(columns=lambda x: x + '1' if x != 'Date' else x)
    return dfEtEx

def EntryExitMaxToMin(dfInterval):
    dfEtEx = dfInterval.groupby('Date')['High'].max().reset_index()
    dfEtEx = pd.merge(dfEtEx, dfInterval[['Date', 'High', 'Datetime']], how='left', on=['Date', 'High']).drop_duplicates(subset=['Date', 'High'], keep='last').reset_index(drop=True).rename(columns={'High': 'Exit', 'Datetime': 'exitDatetime'})
    dfEtEx[['Entry', 'entryDatetime']] = dfEtEx.apply(lambda row: dfInterval.loc[dfInterval[(dfInterval['Date'] == row['Date']) & (dfInterval['Datetime'] <= row['exitDatetime'])]['Low'].idxmin(), ['Low', 'Datetime']], axis=1)
    dfEtEx = pd.merge(dfEtEx, dfInterval[['Date', 'Datetime', 'OpenDay']].drop_duplicates(subset='Date', keep='first').reset_index(drop=True).rename(columns={'Datetime': 'OpenDayDatetime'}), how='left', on='Date')
    dfEtEx = dfEtEx[['Date', 'OpenDayDatetime', 'entryDatetime', 'exitDatetime', 'OpenDay', 'Entry','Exit']]
    dfEtEx['entrytimeDiff'] = ((dfEtEx['entryDatetime'] - dfEtEx['OpenDayDatetime']).dt.total_seconds()/60).astype(int)
    dfEtEx['exittimeDiff'] = ((dfEtEx['exitDatetime'] - dfEtEx['entryDatetime']).dt.total_seconds()/60).astype(int)
    dfEtEx['OpenToEntryLoss'] = ((1-dfEtEx['OpenDay']/dfEtEx['Entry'])*100).round(2)
    dfEtEx['OpenToExitProfit'] = ((1-dfEtEx['OpenDay']/dfEtEx['Exit'])*100).round(2)
    dfEtEx['EtExProfit'] = (((dfEtEx['Exit'] - dfEtEx['Entry'])/dfEtEx['Exit'])*100).round(2)
    dfEtEx = dfEtEx[['Date', 'Entry', 'Exit', 'entrytimeDiff', 'exittimeDiff', 'OpenToEntryLoss', 'OpenToExitProfit', 'EtExProfit']].rename(columns=lambda x: x + '2' if x != 'Date' else x)
    return dfEtEx

def MovingAverage44(df):
    df['44MA'] = df['Close'].rolling(window=44).mean().fillna(0)
    df['44TF'] = df.apply(lambda row: 1 if row['44MA'] <= row['High'] and row['44MA'] >= row['Low'] else 0, axis=1)
    return df

def buy_sell_probability_in_profit_and_loss(df):
    BuyInProfit = len(df[df['maxLow'] == 0])
    SellInLoss = len(df[df['maxHigh'] == 0])
    BuyInLoss = len(df[(df['maxLow'] != 0) & (df['maxHigh'] != 0) & (df['Open'] > df['Close'])])
    SellInProfit = len(df[(df['maxLow'] != 0) & (df['maxHigh'] != 0) & (df['Open'] < df['Close'])])
    Total = BuyInProfit+SellInLoss+BuyInLoss+SellInProfit
    ProbabilityOfCloseTolerance = df['closeTolerance'].astype(int).value_counts()
    ProbabilityOfCloseTolerance = round((ProbabilityOfCloseTolerance/ProbabilityOfCloseTolerance.sum())*100, 2).to_dict()
    ProbabilityOfProfitLoss = df['P/L'].astype(int).value_counts()
    ProbabilityOfProfitLoss = round((ProbabilityOfProfitLoss/ProbabilityOfProfitLoss.sum())*100, 2).to_dict()  
    ProbabilityOfProfitLossTomorrow = {'Profit': round(sum(value for key, value in ProbabilityOfProfitLoss.items() if key >= 0), 2), 'Loss': round(sum(value for key, value in ProbabilityOfProfitLoss.items() if key < 0), 2)}
    ProbabilityOfProfitMT2Percent= round(sum(value for key, value in ProbabilityOfProfitLoss.items() if key >= 2), 2)
    ProbabilityOfLoss1ratio3Percent= round(sum(value for key, value in ProbabilityOfProfitLoss.items() if key <= -1), 2)
    ProbabilityOfmaxHigh = df['maxHigh'].astype(int).value_counts()
    ProbabilityOfmaxHigh = round((ProbabilityOfmaxHigh/ProbabilityOfmaxHigh.sum())*100, 2).to_dict()  
    ProbabilityOfmaxLow = df['maxLow'].astype(int).value_counts()
    ProbabilityOfmaxLow = round((ProbabilityOfmaxLow/ProbabilityOfmaxLow.sum())*100, 2).to_dict()  
    ProbabilityOfpriceBand = df['priceBand'].astype(int).value_counts()
    ProbabilityOfpriceBand = round((ProbabilityOfpriceBand/ProbabilityOfpriceBand.sum())*100, 2).to_dict() 
    buysellProbability = {
        'BuyInProfit MP::HP::MP::HP': round((BuyInProfit/Total)*100, 2),
        'SellInLoss MP::MP::LP::LP': round((SellInLoss/Total)*100, 2),
        'BuyInLoss MP::HP::LP::HP': round((BuyInLoss/Total)*100, 2),
        'SellInProfit MP::HP::LP::LP': round((SellInProfit/Total)*100, 2),
        'ProbabilityOfCloseTolerance': ProbabilityOfCloseTolerance,
        'ProbabilityOfProfitLoss': ProbabilityOfProfitLoss,
        'ProbabilityOfProfitTomorrow': ProbabilityOfProfitLossTomorrow.get('Profit'),
        'ProbabilityOfLossTomorrow': ProbabilityOfProfitLossTomorrow.get('Loss'),
        'ProbabilityOfProfitMT2Percent': ProbabilityOfProfitMT2Percent,
        'ProbabilityOfLoss1ratio3Percent': ProbabilityOfLoss1ratio3Percent,
        'ProbabilityOfmaxHigh': ProbabilityOfmaxHigh,
        'ProbabilityOfmaxLow': ProbabilityOfmaxLow,
        'ProbabilityOfpriceBand': ProbabilityOfpriceBand
        }
    return buysellProbability

def ProbabilityDataProcessing(df, symbol): 
    df['Symbol'] = symbol
    dct = df[['Symbol', 'Date', 'Open', 'High', 'Low', 'Close', 'P/L', 'maxHigh', 'maxLow', 'closeTolerance', 'priceBand']].iloc[-1].to_dict()
    buysellProbability = buy_sell_probability_in_profit_and_loss(df)
    dct = {**dct, **buysellProbability}
    return dct

def fetching_all_stock_data_based_on_todays(symbol):
    symbol = symbol+'.NS'
    df, dfInterval = yfDownload(symbol, '1y', '5m')
    df = formulaPercentage(df)
    df = MovingAverage44(df)
    dfInterval = MovingAverage44(dfInterval)
    dfCandle = pd.merge(pd.merge(dfInterval.groupby('Date') ['CandleP/N_OpenDay'].value_counts().unstack(fill_value=0).reset_index().rename(columns={-1: 'nCandleBelowOpen', 1: 'pCandleAboveOpen'}), dfInterval.groupby('Date') ['CandleP/N'].value_counts().unstack(fill_value=0).reset_index().rename(columns={-1: 'nCandle', 1: 'pCandle'}), how='left', on='Date'), dfInterval.groupby('Date') ['44TF'].value_counts().unstack(fill_value=0).reset_index().rename(columns={1: 'Hits44MA'})[['Date', 'Hits44MA']], how='left', on='Date')
    dfEtEx = pd.merge(EntryExitMinToMax(dfInterval), EntryExitMaxToMin(dfInterval), how='left', on='Date')
    dfItCd = pd.merge(dfCandle, dfEtEx,how='left', on='Date')
    df = pd.merge(df, dfItCd, how='left', on='Date')
    filePath = fr"./Data/Processing/{df['Date'].astype(str).iloc[-1]}/{symbol.split('.')[0]}.xlsx"
    os.makedirs(os.path.dirname(filePath), exist_ok=True)
    df.to_excel(filePath, index=False)
    df = df.dropna().reset_index(drop=True)
    dct = ProbabilityDataProcessing(df, symbol)
    return dct



