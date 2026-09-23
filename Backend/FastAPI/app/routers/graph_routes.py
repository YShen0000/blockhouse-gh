from fastapi import APIRouter, Query, HTTPException
from ..services import graph_services

router = APIRouter(
    prefix="/api/analytics",
    tags=["Graph"],
    responses={404: {"description": "Not found"}},
)


@router.get("/hoodwinked_analyze")
async def hoodwinked_analyze(file_id: str = Query(...), platform: str = Query(...), institution_id: str = Query(...),):
    """
    GET :- /api/analytics/hoodwinked_analyze

    Endpoint to analyze hoodwinked data.

    Args:
        file_id (str): File ID.
        platform (str): Platform name.

    Returns:
        dict: Response message and analysis data.
    """
    try:
        return await graph_services.get_hoodwinked_analyze_plaid(file_id, platform,institution_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/hoodwinked_analyze_plaid")
async def hoodwinked_analyze_plaid(email: str = Query(...), platform: str = Query(...), institution_id: str = Query(...),):
    """
    GET :- /api/analytics/hoodwinked_analyze_plaid

    Endpoint to analyze hoodwinked plaid data.

    Args:
        email (str): User's email address.
        platform (str): Platform name.

    Returns:
        dict: Response message and analysis data.
    """
    try:
        return await graph_services.get_hoodwinked_analyze_plaid(email, platform, institution_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/hoodwinked_graph")
async def hoodwinked_graph(
    platform: str = Query(...),
    institution_id: str = Query(...),
    chart_type: str = Query(...),
    email: str = Query(...),
    stock: str = Query("all_trades"),
    benchmark: str = Query("all_trades"),
    trade_option: str = Query("All Trades"),
    start_date: str = Query(None),
    end_date: str = Query(None),
):
    """
    GET :- /api/analytics/hoodwinked_graph

    Endpoint to generate a hoodwinked graph.

    Args:
        file_id (str): File ID.
        platform (str): Platform name.
        chart_type (str): Type of chart.
        trade_option (str): Trade option.

    Returns:
        dict: Response message and graph data.
    """
    try:
        return await graph_services.get_hoodwinked_graph_plaid(
            platform,
            institution_id,
            chart_type,
            email,
            stock,
            benchmark,
            trade_option,
            start_date,
            end_date,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/hoodwinked_graph_plaid")
async def hoodwinked_graph_plaid(
    platform: str = Query(...),
    institution_id: str = Query(...),
    chart_type: str = Query(...),
    email: str = Query(...),
    stock: str = Query("all_trades"),
    benchmark: str = Query("all_trades"),
    trade_option: str = Query("All Trades"),
    start_date: str = Query(None),
    end_date: str = Query(None),
):
    """
    GET :- /hoodwinked_graph_plaid

    Endpoint to generate a hoodwinked plaid graph.

    Args:
        platform (str): Platform name.
        chart_type (str): Type of chart.
        trade_option (str): Trade option.
        email (str): User's email address.

    Returns:
        dict: Response message and graph data.
    """
    try:
        return await graph_services.get_hoodwinked_graph_plaid(
            platform,
            institution_id,
            chart_type,
            email,
            stock,
            benchmark,
            trade_option,
            start_date,
            end_date,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")