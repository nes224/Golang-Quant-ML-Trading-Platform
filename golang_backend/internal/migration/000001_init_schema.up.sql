CREATE TABLE "checklist_monthly" (
    "id" bigserial PRIMARY KEY,
    "month" varchar,
    "item_name" varchar NOT NULL,
    "count" integer NOT NULL,
    "created_datetime" timestamp,
    "updated_datetime" timestamp NULL
);

CREATE TABLE "historical_candles" (
    "id" bigserial PRIMARY KEY,
    "symbol" varchar NOT NULL,
    "timeframe" varchar NOT NULL,
    "timestamp" timestamp NOT NULL,
    "open" double precision NOT NULL,
    "close" double precision NOT NULL,
    "high" double precision NOT NULL,
    "low" double precision NOT NULL,
    "volume" double precision NOT NULL,
    "created_datetime" timestamp,
    "updated_datetime" timestamp NULL
);

CREATE TABLE "journal_entries" (
    "id" bigserial PRIMARY KEY,
    "symbol" varchar NOT NULL,
    "trade_1" double precision NOT NULL,
    "trade_2" double precision NOT NULL,
    "trade_3" double precision NOT NULL,
    "deposit" double precision NOT NULL,
    "withdraw" double precision NOT NULL,
    "note" varchar,
    "profit" double precision NOT NULL,
    "total" double precision NOT NULL,
    "capital" double precision NOT NULL,
    "winrate" double precision NOT NULL,
    "created_datetime" timestamp,
    "updated_datetime" timestamp NULL
);

CREATE TABLE "market_data" (
    "id" bigserial PRIMARY KEY,
    "symbol" varchar NOT NULL,
    "timeframe" varchar NOT NULL,
    "timestamp" timestamp NOT NULL,
    "open" double precision NOT NULL,
    "close" double precision NOT NULL,
    "high" double precision NOT NULL,
    "low" double precision NOT NULL,
    "volume" double precision NOT NULL,
    "created_datetime" timestamp
);

CREATE TABLE "news_analysis" (
    "id" bigserial PRIMARY KEY,
    "date" varchar NOT NULL,
    "time" varchar NOT NULL,
    "title" varchar NOT NULL,
    "content" varchar,
    "url" varchar,
    "ai_analysis" varchar,
    "sentiment" varchar,
    "impact_score" int DEFAULT 0,
    "tags" varchar,
    "type" varchar,
    "created_datetime" timestamp,
    "updated_datetime" timestamp NULL
);