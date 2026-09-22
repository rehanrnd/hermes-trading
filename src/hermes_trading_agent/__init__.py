"""Hermes trading agent scaffold."""

from .agent_loop import run_reflection_loop, run_reflection_loop_from_market_data
from .bitget import BitgetConfig, BitgetSetupReport, bitget_env_status, build_bitget_setup_report, format_bitget_setup_report, load_bitget_config
from .data import MarketData, load_market_data_csv
from .goal import Goal, load_goal
from .paper import SimulationResult, Trade, reflection_recommendation, run_paper_backtest, run_paper_backtest_from_market_data
from .monitor import DEFAULT_ASSET, DEFAULT_STATE_PATH, DEFAULT_SYMBOL, MarketSnapshot, SignalDecision, TradingMonitorState, build_trading_monitor_state, evaluate_market, fetch_gold_price_snapshot, format_trading_monitor_state, load_trading_monitor_state, run_monitor_cycle, save_trading_monitor_state
from .journal import render_trade_journal_csv, write_trade_journal_csv
from .summary import build_backtest_summary, render_backtest_summary_json, write_backtest_summary_json

__all__ = [
    "BitgetConfig",
    "BitgetSetupReport",
    "Goal",
    "DEFAULT_ASSET",
    "DEFAULT_STATE_PATH",
    "DEFAULT_SYMBOL",
    "MarketData",
    "SimulationResult",
    "MarketSnapshot",
    "SignalDecision",
    "build_trading_monitor_state",
    "evaluate_market",
    "fetch_gold_price_snapshot",
    "format_trading_monitor_state",
    "load_trading_monitor_state",
    "run_monitor_cycle",
    "save_trading_monitor_state",
    "Trade",
    "TradingMonitorState",
    "bitget_env_status",
    "build_bitget_setup_report",
    "format_bitget_setup_report",
    "load_bitget_config",
    "load_goal",
    "load_market_data_csv",
    "reflection_recommendation",
    "render_backtest_summary_json",
    "render_trade_journal_csv",
    "run_paper_backtest",
    "run_paper_backtest_from_market_data",
    "run_reflection_loop",
    "run_reflection_loop_from_market_data",
    "write_backtest_summary_json",
    "write_trade_journal_csv",
]
