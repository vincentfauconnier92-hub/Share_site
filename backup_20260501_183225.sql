--
-- PostgreSQL database dump
--

\restrict pRsr92BY7HuA29A5vOIZ8Zc9tBzKubIibEOqMhu6UB4Op39Bb9oma9kxzl0Hdh3

-- Dumped from database version 16.13
-- Dumped by pg_dump version 16.13

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: assettype; Type: TYPE; Schema: public; Owner: trading
--

CREATE TYPE public.assettype AS ENUM (
    'stock',
    'crypto'
);


ALTER TYPE public.assettype OWNER TO trading;

--
-- Name: tradeaction; Type: TYPE; Schema: public; Owner: trading
--

CREATE TYPE public.tradeaction AS ENUM (
    'buy',
    'sell'
);


ALTER TYPE public.tradeaction OWNER TO trading;

--
-- Name: tradestatus; Type: TYPE; Schema: public; Owner: trading
--

CREATE TYPE public.tradestatus AS ENUM (
    'pending',
    'filled',
    'cancelled',
    'failed'
);


ALTER TYPE public.tradestatus OWNER TO trading;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: portfolio_snapshots; Type: TABLE; Schema: public; Owner: trading
--

CREATE TABLE public.portfolio_snapshots (
    id integer NOT NULL,
    "timestamp" timestamp without time zone,
    portfolio_value double precision NOT NULL,
    open_positions integer,
    realized_pnl double precision,
    capital_deployed double precision
);


ALTER TABLE public.portfolio_snapshots OWNER TO trading;

--
-- Name: portfolio_snapshots_id_seq; Type: SEQUENCE; Schema: public; Owner: trading
--

CREATE SEQUENCE public.portfolio_snapshots_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.portfolio_snapshots_id_seq OWNER TO trading;

--
-- Name: portfolio_snapshots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: trading
--

ALTER SEQUENCE public.portfolio_snapshots_id_seq OWNED BY public.portfolio_snapshots.id;


--
-- Name: positions; Type: TABLE; Schema: public; Owner: trading
--

CREATE TABLE public.positions (
    id integer NOT NULL,
    symbol character varying NOT NULL,
    asset_type character varying NOT NULL,
    strategy character varying NOT NULL,
    quantity double precision NOT NULL,
    entry_price double precision NOT NULL,
    capital_allocated double precision NOT NULL,
    score double precision NOT NULL,
    opened_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.positions OWNER TO trading;

--
-- Name: positions_id_seq; Type: SEQUENCE; Schema: public; Owner: trading
--

CREATE SEQUENCE public.positions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.positions_id_seq OWNER TO trading;

--
-- Name: positions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: trading
--

ALTER SEQUENCE public.positions_id_seq OWNED BY public.positions.id;


--
-- Name: strategy_configs; Type: TABLE; Schema: public; Owner: trading
--

CREATE TABLE public.strategy_configs (
    id integer NOT NULL,
    name character varying NOT NULL,
    symbol character varying NOT NULL,
    asset_type character varying NOT NULL,
    enabled boolean,
    params json,
    stop_loss_pct double precision,
    take_profit_pct double precision,
    position_size_pct double precision
);


ALTER TABLE public.strategy_configs OWNER TO trading;

--
-- Name: strategy_configs_id_seq; Type: SEQUENCE; Schema: public; Owner: trading
--

CREATE SEQUENCE public.strategy_configs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.strategy_configs_id_seq OWNER TO trading;

--
-- Name: strategy_configs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: trading
--

ALTER SEQUENCE public.strategy_configs_id_seq OWNED BY public.strategy_configs.id;


--
-- Name: trades; Type: TABLE; Schema: public; Owner: trading
--

CREATE TABLE public.trades (
    id integer NOT NULL,
    symbol character varying NOT NULL,
    asset_type public.assettype NOT NULL,
    action public.tradeaction NOT NULL,
    quantity double precision NOT NULL,
    price double precision,
    status public.tradestatus,
    strategy character varying,
    broker_order_id character varying,
    created_at timestamp without time zone,
    filled_at timestamp without time zone
);


ALTER TABLE public.trades OWNER TO trading;

--
-- Name: trades_id_seq; Type: SEQUENCE; Schema: public; Owner: trading
--

CREATE SEQUENCE public.trades_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.trades_id_seq OWNER TO trading;

--
-- Name: trades_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: trading
--

ALTER SEQUENCE public.trades_id_seq OWNED BY public.trades.id;


--
-- Name: portfolio_snapshots id; Type: DEFAULT; Schema: public; Owner: trading
--

ALTER TABLE ONLY public.portfolio_snapshots ALTER COLUMN id SET DEFAULT nextval('public.portfolio_snapshots_id_seq'::regclass);


--
-- Name: positions id; Type: DEFAULT; Schema: public; Owner: trading
--

ALTER TABLE ONLY public.positions ALTER COLUMN id SET DEFAULT nextval('public.positions_id_seq'::regclass);


--
-- Name: strategy_configs id; Type: DEFAULT; Schema: public; Owner: trading
--

ALTER TABLE ONLY public.strategy_configs ALTER COLUMN id SET DEFAULT nextval('public.strategy_configs_id_seq'::regclass);


--
-- Name: trades id; Type: DEFAULT; Schema: public; Owner: trading
--

ALTER TABLE ONLY public.trades ALTER COLUMN id SET DEFAULT nextval('public.trades_id_seq'::regclass);


--
-- Data for Name: portfolio_snapshots; Type: TABLE DATA; Schema: public; Owner: trading
--

COPY public.portfolio_snapshots (id, "timestamp", portfolio_value, open_positions, realized_pnl, capital_deployed) FROM stdin;
1	2026-04-30 14:54:04.761971	10000	0	0	0
2	2026-04-30 16:49:24.918377	10000	0	0	0
3	2026-04-30 16:55:00.916874	10000	0	0	0
4	2026-04-30 17:05:17.030068	10000	0	0	0
5	2026-04-30 17:08:15.883424	10000	0	0	0
6	2026-04-30 17:11:16.074942	10000	0	0	0
7	2026-04-30 17:14:15.942908	10000	0	0	0
8	2026-04-30 17:17:15.802639	10000	0	0	0
9	2026-04-30 17:20:15.893842	10000	0	0	0
10	2026-04-30 17:23:15.840747	10000	0	0	0
11	2026-04-30 17:26:15.740358	10000	0	0	0
12	2026-04-30 17:29:15.94224	10000	0	0	0
13	2026-04-30 17:32:15.897567	10000	0	0	0
\.


--
-- Data for Name: positions; Type: TABLE DATA; Schema: public; Owner: trading
--

COPY public.positions (id, symbol, asset_type, strategy, quantity, entry_price, capital_allocated, score, opened_at, updated_at) FROM stdin;
\.


--
-- Data for Name: strategy_configs; Type: TABLE DATA; Schema: public; Owner: trading
--

COPY public.strategy_configs (id, name, symbol, asset_type, enabled, params, stop_loss_pct, take_profit_pct, position_size_pct) FROM stdin;
1	MA Crossover	AAPL	stock	t	{}	5	10	10
\.


--
-- Data for Name: trades; Type: TABLE DATA; Schema: public; Owner: trading
--

COPY public.trades (id, symbol, asset_type, action, quantity, price, status, strategy, broker_order_id, created_at, filled_at) FROM stdin;
1	AAPL	stock	buy	0	0	failed	MA Crossover	\N	2026-04-30 14:54:04.70403	\N
\.


--
-- Name: portfolio_snapshots_id_seq; Type: SEQUENCE SET; Schema: public; Owner: trading
--

SELECT pg_catalog.setval('public.portfolio_snapshots_id_seq', 45, true);


--
-- Name: positions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: trading
--

SELECT pg_catalog.setval('public.positions_id_seq', 1, false);


--
-- Name: strategy_configs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: trading
--

SELECT pg_catalog.setval('public.strategy_configs_id_seq', 1, true);


--
-- Name: trades_id_seq; Type: SEQUENCE SET; Schema: public; Owner: trading
--

SELECT pg_catalog.setval('public.trades_id_seq', 1, true);


--
-- Name: portfolio_snapshots portfolio_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: trading
--

ALTER TABLE ONLY public.portfolio_snapshots
    ADD CONSTRAINT portfolio_snapshots_pkey PRIMARY KEY (id);


--
-- Name: positions positions_pkey; Type: CONSTRAINT; Schema: public; Owner: trading
--

ALTER TABLE ONLY public.positions
    ADD CONSTRAINT positions_pkey PRIMARY KEY (id);


--
-- Name: positions positions_symbol_key; Type: CONSTRAINT; Schema: public; Owner: trading
--

ALTER TABLE ONLY public.positions
    ADD CONSTRAINT positions_symbol_key UNIQUE (symbol);


--
-- Name: strategy_configs strategy_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: trading
--

ALTER TABLE ONLY public.strategy_configs
    ADD CONSTRAINT strategy_configs_pkey PRIMARY KEY (id);


--
-- Name: trades trades_pkey; Type: CONSTRAINT; Schema: public; Owner: trading
--

ALTER TABLE ONLY public.trades
    ADD CONSTRAINT trades_pkey PRIMARY KEY (id);


--
-- Name: ix_portfolio_snapshots_id; Type: INDEX; Schema: public; Owner: trading
--

CREATE INDEX ix_portfolio_snapshots_id ON public.portfolio_snapshots USING btree (id);


--
-- Name: ix_portfolio_snapshots_timestamp; Type: INDEX; Schema: public; Owner: trading
--

CREATE INDEX ix_portfolio_snapshots_timestamp ON public.portfolio_snapshots USING btree ("timestamp");


--
-- Name: ix_positions_id; Type: INDEX; Schema: public; Owner: trading
--

CREATE INDEX ix_positions_id ON public.positions USING btree (id);


--
-- Name: ix_strategy_configs_id; Type: INDEX; Schema: public; Owner: trading
--

CREATE INDEX ix_strategy_configs_id ON public.strategy_configs USING btree (id);


--
-- Name: ix_trades_id; Type: INDEX; Schema: public; Owner: trading
--

CREATE INDEX ix_trades_id ON public.trades USING btree (id);


--
-- PostgreSQL database dump complete
--

\unrestrict pRsr92BY7HuA29A5vOIZ8Zc9tBzKubIibEOqMhu6UB4Op39Bb9oma9kxzl0Hdh3

