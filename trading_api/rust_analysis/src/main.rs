use actix_web::{web, App, HttpResponse, HttpServer, Responder};
use actix_cors::Cors;
use serde::{Deserialize, Serialize};

mod indicators;
mod patterns;
mod smc;
mod sr_zones;

#[derive(Deserialize)]
struct IndicatorRequest {
    prices: Vec<f64>,
    high: Vec<f64>,
    low: Vec<f64>,
    close: Vec<f64>,
}

#[derive(Serialize)]
struct IndicatorResponse {
    ema_50: Vec<f64>,
    ema_200: Vec<f64>,
    rsi: Vec<f64>,
    atr: Vec<f64>,
}

async fn calculate_indicators(req: web::Json<IndicatorRequest>) -> impl Responder {
    let ema_50 = indicators::calculate_ema(&req.prices, 50);
    let ema_200 = indicators::calculate_ema(&req.prices, 200);
    let rsi = indicators::calculate_rsi(&req.prices, 14);
    let atr = indicators::calculate_atr(&req.high, &req.low, &req.close, 14);
    
    HttpResponse::Ok().json(IndicatorResponse {
        ema_50,
        ema_200,
        rsi,
        atr,
    })
}

#[derive(Deserialize)]
struct OHLC {
    open: f64,
    high: f64,
    low: f64,
    close: f64,
}

#[derive(Deserialize)]
struct PatternRequest {
    ohlc: Vec<OHLC>,
}

#[derive(Serialize)]
struct PatternResponse {
    hammer: Vec<bool>,
    inverted_hammer: Vec<bool>,
    hanging_man: Vec<bool>,
    bullish_engulfing: Vec<bool>,
    bearish_engulfing: Vec<bool>,
    dragonfly_doji: Vec<bool>,
    gravestone_doji: Vec<bool>,
    morning_star: Vec<bool>,
    evening_star: Vec<bool>,
}

async fn detect_patterns(req: web::Json<PatternRequest>) -> impl Responder {
    let hammer = patterns::detect_hammer(&req.ohlc);
    let inverted_hammer = patterns::detect_inverted_hammer(&req.ohlc);
    let hanging_man = patterns::detect_hanging_man(&req.ohlc);
    let bullish_engulfing = patterns::detect_bullish_engulfing(&req.ohlc);
    let bearish_engulfing = patterns::detect_bearish_engulfing(&req.ohlc);
    let dragonfly_doji = patterns::detect_dragonfly_doji(&req.ohlc);
    let gravestone_doji = patterns::detect_gravestone_doji(&req.ohlc);
    let morning_star = patterns::detect_morning_star(&req.ohlc);
    let evening_star = patterns::detect_evening_star(&req.ohlc);
    
    HttpResponse::Ok().json(PatternResponse {
        hammer,
        inverted_hammer,
        hanging_man,
        bullish_engulfing,
        bearish_engulfing,
        dragonfly_doji,
        gravestone_doji,
        morning_star,
        evening_star,
    })
}

#[derive(Serialize)]
struct SmcResponse {
    swing_highs: Vec<Option<f64>>,
    swing_lows: Vec<Option<f64>>,
    fvg_bullish: Vec<bool>,
    fvg_bearish: Vec<bool>,
    ob_bullish: Vec<bool>,
    ob_bearish: Vec<bool>,
    sweep_bullish: Vec<bool>,
    sweep_bearish: Vec<bool>,
    fvg_zones: Vec<smc::FvgZone>,
    ob_zones: Vec<smc::OrderBlockZone>,
    sr_zones: Vec<sr_zones::SrZone>,
}

async fn analyze_smc(req: web::Json<PatternRequest>) -> impl Responder {
    let high: Vec<f64> = req.ohlc.iter().map(|x| x.high).collect();
    let low: Vec<f64> = req.ohlc.iter().map(|x| x.low).collect();
    let close: Vec<f64> = req.ohlc.iter().map(|x| x.close).collect();
    let current_price = req.ohlc.last().map(|x| x.close).unwrap_or(0.0);
    
    let (swing_highs, swing_lows) = smc::identify_swing_points(&high, &low, 5);
    
    // Get both boolean and zone data
    let (fvg_bullish, fvg_bearish) = smc::detect_fvg(&req.ohlc);
    let fvg_zones = smc::detect_fvg_zones(&req.ohlc);
    
    let (ob_bullish, ob_bearish) = smc::detect_order_blocks(&req.ohlc);
    let ob_zones = smc::detect_order_block_zones(&req.ohlc);
    
    let (sweep_bullish, sweep_bearish) = smc::detect_liquidity_sweep(&high, &low, &close, 20);
    
    let zones = sr_zones::identify_sr_zones(
        &swing_highs, 
        &swing_lows, 
        current_price, 
        0.002, 
        2
    );
    
    HttpResponse::Ok().json(SmcResponse {
        swing_highs,
        swing_lows,
        fvg_bullish,
        fvg_bearish,
        ob_bullish,
        ob_bearish,
        sweep_bullish,
        sweep_bearish,
        fvg_zones,
        ob_zones,
        sr_zones: zones,
    })
}

async fn health_check() -> impl Responder {
    HttpResponse::Ok().json(serde_json::json!({
        "status": "ok",
        "service": "rust_analysis",
        "version": "0.1.0"
    }))
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    println!("🦀 Rust Analysis API starting on http://127.0.0.1:8001");
    
    HttpServer::new(|| {
        // CORS configuration - allow all origins for development
        let cors = Cors::permissive();
        
        App::new()
            .wrap(cors)
            .route("/health", web::get().to(health_check))
            .route("/calculate/indicators", web::post().to(calculate_indicators))
            .route("/detect/patterns", web::post().to(detect_patterns))
            .route("/analyze/smc", web::post().to(analyze_smc))
    })
    .bind(("127.0.0.1", 8001))?
    .run()
    .await
}
