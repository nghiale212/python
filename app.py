import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
import pandas as pd
import ta
from vnstock import Vnstock
from datetime import datetime, timedelta
import numpy as np

app = Dash(__name__, suppress_callback_exceptions=True)
app.scripts.config.serve_locally = True  # Tránh tải các scripts từ CDN
server = app.server

# Thêm CSS để ẩn console warnings
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <script type="text/javascript">
            console.warn = function() {};  // Suppress warnings
        </script>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Layout Dash
app.layout = html.Div(style={'backgroundColor': '#1a1a1a', 'padding': '20px'}, children=[
    html.H1("Phân tích Cổ phiếu Việt Nam", style={'textAlign': 'center', 'color': '#FFFFFF'}),
    dcc.Dropdown(
        id='stock-picker',
        options=[
            {'label': 'Vinamilk (VNM)', 'value': 'VNM'},
            {'label': 'FPT Corporation (FPT)', 'value': 'FPT'},
            {'label': 'Vietcombank (VCB)', 'value': 'VCB'}
        ],
        value='VNM',
        style={'width': '50%', 'margin': 'auto', 'color': '#000000'}
    ),
    html.Div(id='error-message', style={'color': 'red', 'textAlign': 'center', 'margin': '10px'}),
    dcc.Graph(id='candlestick-graph'),
    dcc.Graph(id='rsi-graph'),
    dcc.Graph(id='volume-graph')
])

@app.callback(
    [Output('candlestick-graph', 'figure'),
     Output('rsi-graph', 'figure'),
     Output('volume-graph', 'figure'),
     Output('error-message', 'children')],
    Input('stock-picker', 'value')
)
def update_graphs(stock):
    error_message = ""
    try:
        # Lấy dữ liệu 1 năm gần nhất
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        # Sử dụng vnstock để lấy dữ liệu với cú pháp mới
        stock_data = Vnstock().stock(symbol=stock, source='TCBS')
        df = stock_data.quote.history(
            start=start_date.strftime("%Y-%m-%d"), 
            end=end_date.strftime("%Y-%m-%d"),
            interval='1D'
        )

        if df is None or df.empty:
            error_message = f"Không thể tải dữ liệu cho {stock}. Vui lòng thử mã khác."
            return go.Figure(), go.Figure(), go.Figure(), error_message

        # Đổi tên cột cho phù hợp
        df = df.rename(columns={
            'time': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        })

        # Đảm bảo Date ở định dạng datetime
        df['Date'] = pd.to_datetime(df['Date'])

        # Bollinger Bands
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        df['StdDev'] = df['Close'].rolling(window=20).std()
        df['UpperBand'] = df['SMA20'] + 2 * df['StdDev']
        df['LowerBand'] = df['SMA20'] - 2 * df['StdDev']

        # RSI
        df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()

        # Candlestick
        candlestick_fig = go.Figure()
        candlestick_fig.add_trace(go.Candlestick(
            x=df['Date'],
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='Candlestick'
        ))
        candlestick_fig.add_trace(go.Scatter(x=df['Date'], y=df['UpperBand'], mode='lines', name='Upper Band', line=dict(color='red', dash='dash')))
        candlestick_fig.add_trace(go.Scatter(x=df['Date'], y=df['LowerBand'], mode='lines', name='Lower Band', line=dict(color='green', dash='dash')))
        candlestick_fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA20'], mode='lines', name='SMA20', line=dict(color='orange')))
        candlestick_fig.update_layout(
            title=f'Biểu đồ nến {stock}',
            xaxis_title='Ngày',
            yaxis_title='Giá',
            template='plotly_dark',
            height=500
        )

        # RSI Graph
        rsi_fig = go.Figure()
        rsi_fig.add_trace(go.Scatter(x=df['Date'], y=df['RSI'], mode='lines', name='RSI', line=dict(color='purple')))
        rsi_fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
        rsi_fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")
        rsi_fig.update_layout(
            title="Chỉ số RSI",
            xaxis_title='Ngày',
            yaxis_title='RSI',
            template='plotly_dark',
            height=300
        )

        # Volume Graph
        volume_fig = go.Figure()
        volume_fig.add_trace(go.Bar(x=df['Date'], y=df['Volume'], name='Khối lượng', marker_color='blue'))
        volume_fig.update_layout(
            title="Khối lượng giao dịch",
            xaxis_title='Ngày',
            yaxis_title='Volume',
            template='plotly_dark',
            height=300
        )

        return candlestick_fig, rsi_fig, volume_fig, error_message

    except Exception as e:
        error_message = f"Lỗi khi tải dữ liệu: {str(e)}"
        print(f"Error details: {str(e)}")  # In ra console để debug
        return go.Figure(), go.Figure(), go.Figure(), error_message

if __name__ == '__main__':
    app.run_server(debug=True)
