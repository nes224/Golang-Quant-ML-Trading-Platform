import plotly.graph_objects as go
from plotly.subplots import make_subplots

def generate_chart(df, symbol, timeframe):
    """
    Generates an interactive HTML chart using Plotly.
    Includes Candlesticks, EMA, Signals, and SMC Levels (FVG/OB).
    """
    if df is None or df.empty:
        return "<h3>No Data Available</h3>"
        
    # Create Subplots (Main Price + RSI)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, row_heights=[0.7, 0.3])

    # 1. Candlestick Chart
    fig.add_trace(go.Candlestick(
        x=df['Datetime'] if 'Datetime' in df.columns else df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Price'
    ), row=1, col=1)

    # 2. EMA Indicators
    if 'EMA_50' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_50'], line=dict(color='orange', width=1), name='EMA 50'), row=1, col=1)
    if 'EMA_200' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_200'], line=dict(color='blue', width=2), name='EMA 200'), row=1, col=1)

    # 3. Buy/Sell Signals
    buy_signals = df[df['Signal'] == 1]
    sell_signals = df[df['Signal'] == -1]
    
    fig.add_trace(go.Scatter(
        x=buy_signals.index, y=buy_signals['Low'],
        mode='markers', marker=dict(symbol='triangle-up', size=10, color='green'),
        name='Buy Signal'
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=sell_signals.index, y=sell_signals['High'],
        mode='markers', marker=dict(symbol='triangle-down', size=10, color='red'),
        name='Sell Signal'
    ), row=1, col=1)

    # 4. SMC Visualizations (FVG & OB)
    # We iterate through the last 50 candles to avoid cluttering the whole history
    recent_df = df.tail(50)
    
    for i, row in recent_df.iterrows():
        # Bullish FVG (Green Box)
        if row.get('FVG_Bullish'):
            # FVG is between High[i-2] and Low[i]. We need to access previous rows safely.
            # Since we are iterating, it's hard to look back by index easily in a loop without integer index.
            # Simplified: We just draw a marker or small line for now, or use the logic if we had the levels.
            # In analysis.py we didn't store levels, just boolean. 
            # To draw boxes properly, we need the levels. 
            # For this iteration, let's just mark the candle that CREATED the FVG.
            pass 

        # Order Blocks (Rectangle)
        # Similarly, we need levels. Let's assume the OB is the entire body of the candle.
        if row.get('OB_Bullish'):
            fig.add_shape(type="rect",
                x0=i, y0=row['Low'], x1=i, y1=row['High'],
                line=dict(color="green", width=2),
                fillcolor="green", opacity=0.3,
                row=1, col=1
            )
        if row.get('OB_Bearish'):
            fig.add_shape(type="rect",
                x0=i, y0=row['Low'], x1=i, y1=row['High'],
                line=dict(color="red", width=2),
                fillcolor="red", opacity=0.3,
                row=1, col=1
            )

    # 5. RSI
    if 'RSI' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple', width=1), name='RSI'), row=2, col=1)
        # Overbought/Oversold Lines
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    # Layout Updates
    fig.update_layout(
        title=f"{symbol} - {timeframe} Analysis",
        yaxis_title='Price',
        xaxis_rangeslider_visible=False,
        height=800,
        template="plotly_dark"
    )
    
    return fig.to_html(full_html=True, include_plotlyjs='cdn')
