import pandas as pd

from ui.charts3d import time_series_figure, prediction_figure, comparison_figure


def test_time_series_preserves_values_and_station_groups():
    df = pd.DataFrame({'station_id':['A','B','A'], 'time':['2026-01-01','2026-01-01','2026-01-02'], 'level':[1.,2.,3.]})
    fig = time_series_figure(df, 'time', 'level', '水位')
    assert len(fig.data) == 2
    assert list(fig.data[0].x) == [0.,24.]
    assert list(fig.data[0].z) == [1.,3.]
    assert fig.data[1].type == 'scatter3d'


def test_prediction_uses_observed_flow_and_level_axes():
    df = pd.DataFrame({'predict_time':['2026-01-01','2026-01-02'], 'predicted_flow':[12.,13.], 'predicted_level':[3.1,3.2]})
    trace = prediction_figure(df).data[0]
    assert list(trace.y) == [12.,13.]
    assert list(trace.z) == [3.1,3.2]


def test_empty_time_series_is_supported():
    assert len(time_series_figure(pd.DataFrame(), 'time', 'level', '水位').data) == 0


def test_comparison_uses_unscaled_model_values():
    df = pd.DataFrame([dict(plan_code='A', max_level=4.2, energy_index=82., drainage_volume=90., score=91.)])
    trace = comparison_figure(df).data[0]
    assert trace.x[0] == 4.2 and trace.y[0] == 82. and trace.z[0] == 90.
