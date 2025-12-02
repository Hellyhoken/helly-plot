# helly-plot

A Python GUI application for loading, merging, and plotting CSV data with real-time updates.

## Features

- **Load Multiple CSV Files**: Import one or more CSV files at once
- **Flexible Merging Options**: 
  - Concatenate (Stack Rows)
  - Concatenate (Side by Side)
  - Inner Join
  - Outer Join
  - Left Join
- **Multiple Plot Types**:
  - Line plots
  - Scatter plots
  - Bar charts
  - Histograms
  - Area plots
  - Box plots
- **Plot Customization**:
  - Select X and Y columns
  - Multiple Y columns support
  - Custom titles and axis labels
  - Line styles and markers
  - Opacity control
  - Grid and legend toggles
- **Real-time Updates**: Plot updates automatically as you change settings
- **Export Options**: Save plots as PNG or SVG

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/Hellyhoken/helly-plot.git
   cd helly-plot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the application:
```bash
python csv_plotter.py
```

### Quick Start

1. Click "Add Files" to load one or more CSV files
2. Choose a merge option if you have multiple files
3. Click "Apply Merge" to combine the data
4. Switch to the "Plot Settings" tab
5. Select plot type and columns
6. Customize labels and styles as needed
7. Save your plot using "Save as PNG" or "Save as SVG"

## Requirements

- Python 3.8+
- PyQt6
- matplotlib
- pandas
- numpy

## License

MIT License
