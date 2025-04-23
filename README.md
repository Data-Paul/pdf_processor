# PDF Processor

A tool for processing PDF files and extracting structured data into CSV format. This application can be run either as a GUI application or as a Docker container.

## Features

- Extract tables from PDF files
- Convert PDF data to CSV format
- Support for multiple table types (education, work experience, skills, etc.)
- GUI interface for easy use
- Docker support for automated processing
- Progress tracking and error handling

## Installation

### Option 1: Direct Installation

1. Clone the repository:
```bash
git clone https://github.com/Data-Paul/pdf_processor.git
cd pdf_processor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python src/main.py
```

### Option 2: Docker Installation

1. Build the Docker image:
```bash
docker build -t pdf-processor .
```

2. Run the container:
```bash
docker run -it \
    -v "$(pwd)/input:/data/input" \
    -v "$(pwd)/output:/data/output" \
    pdf-processor
```

Or using docker-compose:
```bash
docker-compose up
```

## Usage

### GUI Mode

1. Launch the application
2. Select input directory containing PDF files
3. Select output directory for processed files
4. Click "Process PDFs" to start processing
5. Monitor progress in the progress bar
6. View results in the output directory

### Docker Mode

1. Place PDF files in the `input` directory
2. Run the Docker container
3. Find processed files in the `output` directory

## Output Format

The processor creates the following files for each PDF:

- `person_info.csv`: Personal information
- `education.csv`: Education history
- `work_experience.csv`: Work experience
- `skills.csv`: Skills and qualifications
- `traits.csv`: Personal traits and characteristics
- `README.txt`: Processing information and file list

## Requirements

- Python 3.9 or higher
- Docker (optional)
- Required Python packages (see requirements.txt)

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 