import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

class ChartDrawer:
    """
    Analyzes a Pandas DataFrame and automatically selects and renders
    the most appropriate chart type using Plotly.
    Supports volume charts, multi-series, theme synchronization, and chart switching.
    """
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        # Brand Colors
        self.primary_color = "#0056D2"
        self.success_color = "#10b981"
        self.warning_color = "#f59e0b"
        self.theme_colors = [self.primary_color, self.success_color, self.warning_color, "#ef4444", "#8b5cf6", "#ec4899"]

    def _get_plotly_template(self):
        """Returns the appropriate Plotly template based on Streamlit theme."""
        is_dark = st.get_option("theme.base") == "dark" or st.get_option("theme.base") is None
        return "plotly_dark" if is_dark else "plotly_white"

    def get_fig(self, df_input=None, chart_type="bar", x_col=None, y_cols=None):
        """
        Generates a Plotly figure.
        Forces X-axis to be categorical to prevent "wide bar" issues with numeric IDs.
        Uses df_input if provided (useful for passing pre-sorted data).
        """
        # Allow passing a specific DF (e.g. sorted) or fallback to self.df
        df_to_use = df_input if df_input is not None else self.df

        if df_to_use.empty:
            return None
        
        # If dataset is single scalar, don't try to plot
        if len(df_to_use) == 1 and len(df_to_use.columns) < 2:
            return None
            
        template = self._get_plotly_template()
        
        # 1. Determine X-axis (Categorical/Time)
        if not x_col:
            # Prioritize date/string columns, fallback to first column
            for col in df_to_use.columns:
                if pd.api.types.is_object_dtype(df_to_use[col]) or pd.api.types.is_datetime64_any_dtype(df_to_use[col]):
                    x_col = col
                    break
            if not x_col: x_col = df_to_use.columns[0]

        # 2. Determine Y-axis (Numeric) - EXCLUDING ID FIELDS
        if not y_cols:
            # TRY TO CONVERT OBJECT COLUMNS TO NUMERIC (Handle Decimals/Strings from DB)
            temp_y_cols = [
                col for col in df_to_use.columns 
                if col != x_col and not any(x in col.lower() for x in ['id', 'key', 'code', 'pk', 'fk'])
            ]
            
            for col in temp_y_cols:
                if pd.api.types.is_object_dtype(df_to_use[col]):
                    # Check if the first non-null value is convertable to float
                    first_val = df_to_use[col].dropna().iloc[0] if not df_to_use[col].dropna().empty else None
                    if first_val is not None:
                        try:
                            pd.to_numeric(df_to_use[col], errors='raise')
                            df_to_use[col] = pd.to_numeric(df_to_use[col], errors='coerce')
                        except:
                            pass # Not numeric data

            y_cols = [
                col for col in df_to_use.columns 
                if pd.api.types.is_numeric_dtype(df_to_use[col]) 
                and not any(x in col.lower() for x in ['id', 'key', 'code', 'pk', 'fk'])
            ]
            
        # 3. Prepare Data for Plotting
        # IMPORTANT: We assume df_to_use is ALREADY sorted by the App logic.
        # We just limit rows for performance.
        df_plot = df_to_use.head(50).copy()

        # CRITICAL FIX: Force X-column to string to ensure it's treated as a Category
        # This stops numeric IDs (like Site ID 400) from creating a massive continuous axis
        df_plot[x_col] = df_plot[x_col].astype(str)

        # 4. Handle Volume Logic (if no numeric Y data exists)
        if not y_cols:
            # Use value_counts but respect the order of the input dataframe
            # This ensures that if the user/app sorted the table by Date, the chart follows Date, not Count.
            
            # 1. Get counts (unordered/arbitrary)
            counts = df_to_use[x_col].value_counts(sort=False).reset_index()
            counts.columns = [x_col, 'Count']
            
            # 2. Determine correct order based on input dataframe
            # Get unique values in order of appearance from the sorted table
            ordered_cats = df_to_use[x_col].unique()
            
            # 3. Reorder counts to match input dataframe order
            counts = counts.set_index(x_col)
            # Reindex forces the order to match df_to_use's unique value appearance
            counts = counts.reindex(ordered_cats).reset_index()
            # Rename columns back properly (reindex can mess with index name)
            counts.columns = [x_col, 'Count']
            
            # 4. Select top 20 (now top 20 by input sort order)
            df_plot = counts.head(20)
            
            df_plot[x_col] = df_plot[x_col].astype(str) 
            y_cols = ['Count']

        # 5. Generate Chart based on Type
        plot_args = {
            "data_frame": df_plot,
            "x": x_col,
            "y": y_cols[:5], # Limit to top 5 series to prevent clutter
            "title": f"Analysis by {x_col}",
            "template": template,
            "color_discrete_sequence": self.theme_colors
        }

        if chart_type == "line":
            fig = px.line(**plot_args, markers=True)
        elif chart_type == "scatter":
            fig = px.scatter(**plot_args)
        elif chart_type == "area":
            fig = px.area(**plot_args)
        elif chart_type == "pie":
            val_col = y_cols[0] if y_cols else df_plot.columns[1]
            fig = px.pie(
                df_plot, 
                names=x_col, 
                values=val_col, 
                title=f"Distribution of {val_col}",
                template=template,
                color_discrete_sequence=self.theme_colors
            )
        else:
            # Default to Bar
            fig = px.bar(**plot_args, barmode='group')

        # 6. Final Layout Polish
        fig.update_layout(
            title_x=0.5, 
            legend_title_text="", 
            legend_orientation="h", 
            legend_y=-0.2,
            margin=dict(t=50, b=50),
            hovermode="x unified"
        )
        
        if chart_type != "pie":
            fig.update_xaxes(type='category', categoryorder='trace', tickangle=45 if len(df_plot) > 5 else 0)
            
            # --- DYNAMIC ZOOM & PRECISION LOGIC ---
            # If data variation is low, zoom in the Y-axis to show differences.
            if y_cols:
                primary_y = y_cols[0]
                vals = df_plot[primary_y].dropna()
                if not vals.empty:
                    y_min = float(vals.min())
                    y_max = float(vals.max())
                    y_range = y_max - y_min
                    
                    # Force precision on Y-axis and Hover labels for small values
                    fig.update_yaxes(tickformat=".2f", hoverformat=".3f")
                    
                    # Heuristic: If variance is less than 30% of the max value
                    if y_max != 0 and (y_range / y_max) < 0.3:
                        # Set a tighter range (e.g. 10% padding around the data)
                        padding = y_range * 0.1 if y_range > 0 else y_max * 0.05
                        fig.update_yaxes(range=[y_min - padding, y_max + padding])
        
        return fig

    def draw_chart(self, chart_type="bar"):
        return self.get_fig(chart_type=chart_type)