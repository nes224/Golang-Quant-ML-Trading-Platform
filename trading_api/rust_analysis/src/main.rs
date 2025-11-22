use actix_web::{web, App, HttpResponse, HttpServer, Responder};
use actix_cors::Cors;
use serde::{Deserialize, Serialize};

mod indicators;
mod patterns;

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
}

async fn detect_patterns(req: web::Json<PatternRequest>) -> impl Responder {
    let hammer = patterns::detect_hammer(&req.ohlc);
    let inverted_hammer = patterns::detect_inverted_hammer(&req.ohlc);
    let hanging_man = patterns::detect_hanging_man(&req.ohlc);
    let bullish_engulfing = patterns::detect_bullish_engulfing(&req.ohlc);
    let bearish_engulfing = patterns::detect_bearish_engulfing(&req.ohlc);
    
    HttpResponse::Ok().json(PatternResponse {
        hammer,
        inverted_hammer,
        hanging_man,
        bullish_engulfing,
        bearish_engulfing,
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
    println!("🚀 Starting Rust Analysis Service on http://localhost:8001");
    
    HttpServer::new(|| {
        let cors = Cors::permissive(); // Allow all origins for development
        
        App::new()
            .wrap(cors)
            .route("/health", web::get().to(health_check))
            .route("/calculate/indicators", web::post().to(calculate_indicators))
            .route("/detect/patterns", web::post().to(detect_patterns))
    })
    .bind(("127.0.0.1", 8001))?
    .run()
    .await
}
