def test_ui_pages_and_components_import():
    from src.ui.components import chart_workspace, market_bar, research_workspace, scanner_workspace, trade_lifecycle_panel, watchlist, workspace_toolbar
    from src.ui.pages import backtest_workspace, research_page, scanner_page, trading_workspace

    assert chart_workspace is not None
    assert market_bar is not None
    assert research_workspace is not None
    assert scanner_workspace is not None
    assert trade_lifecycle_panel is not None
    assert watchlist is not None
    assert workspace_toolbar is not None
    assert backtest_workspace is not None
    assert research_page is not None
    assert scanner_page is not None
    assert trading_workspace is not None
