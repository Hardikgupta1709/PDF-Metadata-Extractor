# PDF Metadata Extractor

> An intelligent tool for extracting structured metadata from research papers and PDF documents using machine learning-powered document understanding.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![GROBID](https://img.shields.io/badge/GROBID-0.8.0-green)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Overview

This tool automatically extracts valuable information from PDF documents, with particular focus on academic research papers. It leverages GROBID (GeneRation Of BIbliographic Data), a machine learning library trained on millions of scientific documents, to intelligently parse and structure document content.

### Key Features

The extractor identifies and extracts:

- **Title** - Document title and heading structure
- **Authors** - Complete list of authors with proper name parsing
- **Email Addresses** - Contact information embedded in the document
- **Abstract** - Paper summary and overview
- **Keywords** - Key terms and topic identifiers
- **Publication Date** - Publishing information
- **Body Text** - Full text content with structural preservation

### Use Cases

This tool is designed for:

- **Academic Researchers** - Cataloging and organizing large collections of research papers
- **Digital Libraries** - Building searchable databases and metadata catalogs
- **Literature Review** - Systematic analysis of multiple papers for meta-research
- **Citation Management** - Extracting bibliographic information automatically
- **Contact Discovery** - Finding author contact information for collaboration

---

## Technical Architecture

The extraction pipeline follows a three-stage process:

```
Step 1: Document Upload
        |
        v
Step 2: GROBID Processing
        - Machine learning-based document analysis
        - Layout understanding and section identification
        - Structural element recognition
        |
        v
Step 3: Metadata Extraction
        - Title and author parsing
        - Abstract identification
        - Reference extraction
        |
        v
Step 4: Text Processing
        - Full text extraction
        - Email pattern matching
        - Contact information discovery
        |
        v
Step 5: Output Generation
        - JSON structured data
        - CSV tabular format
        - Web interface display
```

### Technology Stack

- **GROBID 0.8.0** - Machine learning document parser
- **Python 3.8+** - Core processing language
- **Streamlit** - Web interface framework
- **Docker** - Containerized GROBID deployment
- **PyPDF2/pdfplumber** - PDF text extraction libraries

---

## Getting Started

### System Requirements

Before installation, ensure your system meets these requirements:

- Python 3.8 or higher
- Docker 20.10 or higher
- 4GB RAM minimum (8GB recommended)
- 3GB available disk space for Docker images
- Internet connection for initial setup

### Installation Guide

#### Step 1: Verify Python Installation

Open your terminal and check your Python version:

```bash
python --version
```

or

```bash
python3 --version
```

You should see output indicating Python 3.8 or higher. If Python is not installed, download it from [python.org](https://www.python.org/downloads/).

#### Step 2: Install Docker

Docker is required to run the GROBID server. Check if Docker is installed:

```bash
docker --version
```

If Docker is not installed, download the appropriate version:
- **macOS**: [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop)
- **Windows**: [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
- **Linux**: Follow the installation instructions for your distribution from [Docker Documentation](https://docs.docker.com/engine/install/)

#### Step 3: Clone the Repository

Using Git:
```bash
git clone https://github.com/yourusername/pdf-metadata-extractor.git
cd pdf-metadata-extractor
```

Or download and extract the ZIP file from the repository.

#### Step 4: Set Up Virtual Environment

Create an isolated Python environment for the project:

```bash
python -m venv venv
```

Activate the virtual environment:

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

When activated, your command prompt will show `(venv)` at the beginning.

#### Step 5: Install Python Dependencies

Install all required packages:

```bash
pip install -r requirements.txt
```

This installs:
- requests (HTTP client for GROBID API)
- PyPDF2 (PDF processing)
- pdfplumber (Advanced PDF text extraction)
- streamlit (Web interface)

#### Step 6: Configure GROBID Server

The configuration file is located at `config/config.ini`. By default, it points to:

```ini
[GROBID]
server = http://localhost:8070
```

Modify this if you're running GROBID on a different host or port.

#### Step 7: Start GROBID Server

Open a new terminal window and run:

```bash
docker run -t --rm -p 8070:8070 --platform linux/amd64 lfoppiano/grobid:0.8.0
```

**Note**: The first run will download approximately 2GB of data. Subsequent starts are instantaneous.

Keep this terminal window open. GROBID must be running for the extractor to function.

#### Step 8: Verify GROBID Status

In your original terminal (with virtual environment activated), test the connection:

```bash
curl http://localhost:8070/api/isalive
```

Expected response: `true`

---

## Usage Instructions

### Web Interface (Recommended)

The Streamlit web interface provides an intuitive graphical interface for document processing.

#### Starting the Application

```bash
streamlit run app.py
```

The application will automatically open in your default browser at `http://localhost:8501`.

#### Processing Documents

1. Use the file uploader to select a PDF document
2. Click "Extract Metadata" to begin processing
3. Review the extracted information displayed on screen
4. Download results in JSON or CSV format as needed

### Command Line Interface

The command line interface is suitable for batch processing and automation.

#### Basic Usage

```bash
python main.py path/to/your/document.pdf
```

#### With Custom Output Directory

```bash
python main.py path/to/document.pdf --output_dir custom/output/path
```

#### Output Files

Results are saved in the specified output directory (default: `data/output/`):
- `document_name.json` - Structured JSON format
- `document_name.csv` - Tabular CSV format

### Batch Processing

Process multiple PDFs in a directory:

```bash
for pdf in data/input/*.pdf; do
    python main.py "$pdf"
done
```

---

## Project Structure

```
pdf-metadata-extractor/
│
├── main.py                      # Command-line entry point
├── app.py                       # Streamlit web interface
├── requirements.txt             # Python package dependencies
├── README.md                    # Project documentation
│
├── config/
│   └── config.ini              # GROBID server configuration
│
├── src/
│   ├── __init__.py
│   ├── parser/
│   │   ├── __init__.py
│   │   ├── grobid_client.py    # GROBID API integration
│   │   └── email_extractor.py  # Text and email extraction
│   └── utils/
│       ├── __init__.py
│       └── file_utils.py       # File I/O operations
│
└── data/
    ├── input/                   # Source PDF documents
    └── output/                  # Extracted metadata results
```

---

## Configuration

### GROBID Server Settings

Edit `config/config.ini` to modify the GROBID server location:

```ini
[GROBID]
server = http://localhost:8070
```

For remote GROBID installations, update the URL accordingly:

```ini
[GROBID]
server = http://remote-server.com:8070
```

### Python Path Configuration

The application automatically adds the `src` directory to the Python path. If you encounter import issues, verify that all `__init__.py` files exist in:
- `src/`
- `src/parser/`
- `src/utils/`

---

## Troubleshooting

### Port Conflict (8070 already in use)

**Symptom**: Error message indicating port 8070 is already allocated

**Solution**: 
```bash
# Check if GROBID is already running
curl http://localhost:8070/api/isalive

# If you need to restart, find and stop the existing container
docker ps
docker stop <container_id>

# Start a fresh instance
docker run -t --rm -p 8070:8070 --platform linux/amd64 lfoppiano/grobid:0.8.0
```

### Missing Python Modules

**Symptom**: `ModuleNotFoundError` when running the application

**Solution**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Empty or Incomplete Extraction Results

**Possible Causes**:

1. **Scanned Documents**: GROBID works optimally with text-based PDFs. Scanned images require OCR preprocessing.

2. **GROBID Server Not Running**: Verify server status with `curl http://localhost:8070/api/isalive`

3. **Malformed PDF**: Try processing a known-good document to verify the system is functioning:
   ```bash
   curl -o data/input/test.pdf "https://arxiv.org/pdf/1706.03762.pdf"
   python main.py data/input/test.pdf
   ```

### Import Errors in Streamlit

**Symptom**: Module import failures when running `streamlit run app.py`

**Solution**:
```bash
# Clear Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +

# Restart Streamlit
streamlit run app.py
```

### Docker Performance Issues

**Symptom**: Slow GROBID processing or timeouts

**Solution**: Allocate more resources to Docker:
```bash
docker run -t --rm -p 8070:8070 --memory="4g" --cpus="2" lfoppiano/grobid:0.8.0
```

---

## Advanced Usage

### Custom GROBID Configuration

For advanced users who need to customize GROBID settings, you can mount a custom configuration:

```bash
docker run -t --rm -p 8070:8070 \
    -v /path/to/custom/config:/opt/grobid/grobid-home/config \
    lfoppiano/grobid:0.8.0
```

### API Integration

The extraction functionality can be integrated into other Python applications:

```python
from parser.grobid_client import parse_pdf_with_grobid, extract_metadata_from_tei
from parser.email_extractor import extract_full_text, find_emails

# Process a PDF
tei_xml = parse_pdf_with_grobid('document.pdf', 'http://localhost:8070')
metadata = extract_metadata_from_tei(tei_xml)

# Extract emails
full_text = extract_full_text('document.pdf')
emails = find_emails(full_text)
metadata['emails'] = emails
```

---

## Performance Considerations

### Processing Speed

- Average processing time: 2-5 seconds per document
- Batch processing: Approximately 700-1000 documents per hour
- Network latency to GROBID server affects performance

### Resource Usage

- GROBID container: ~2GB RAM during processing
- Python application: ~100-200MB RAM
- Disk space: ~50MB per 1000 processed documents (output files)

### Optimization Tips

1. Run GROBID on a dedicated server for production use
2. Use batch processing for large document collections
3. Implement parallel processing for multi-core systems
4. Cache results to avoid reprocessing unchanged documents

---

## Dependencies

### Core Requirements

```
requests>=2.31.0       # HTTP client for GROBID API
PyPDF2>=3.0.0         # PDF document processing
pdfplumber>=0.10.0    # Advanced PDF text extraction
streamlit>=1.30.0     # Web interface framework
```

### Optional Enhancements

```
Pillow>=10.0.0        # Image processing support
watchdog>=3.0.0       # File system monitoring
```

---

## Contributing

Contributions to improve the project are welcome. Please follow these guidelines:

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes with appropriate tests
4. Ensure code follows PEP 8 style guidelines
5. Commit with descriptive messages: `git commit -m 'Add feature: description'`
6. Push to your fork: `git push origin feature/your-feature-name`
7. Submit a pull request with detailed description

### Code Style

- Follow PEP 8 guidelines for Python code
- Use meaningful variable and function names
- Include docstrings for all functions and classes
- Add comments for complex logic

### Testing

Before submitting a pull request:
- Test with multiple PDF types (text-based, scanned, mixed)
- Verify both CLI and web interfaces function correctly
- Ensure no regression in existing functionality

---

## License

This project is licensed under the MIT License. See the LICENSE file for complete terms.

---

## Acknowledgments

This project builds upon the work of:

- **GROBID Team** - For developing and maintaining the core document parsing engine
- **Streamlit** - For providing an excellent framework for rapid web application development
- **Python PDF Processing Community** - For tools like PyPDF2 and pdfplumber

---

## Support and Contact

For issues, questions, or suggestions:

1. Check the Troubleshooting section above
2. Review [GROBID documentation](https://grobid.readthedocs.io/)
3. Open an issue on GitHub with:
   - Detailed problem description
   - Steps to reproduce
   - Error messages and logs
   - System information (OS, Python version)

---

## Future Development

Planned enhancements include:

- Batch processing web interface
- Support for additional document formats (DOCX, HTML)
- Citation network extraction and visualization
- Multi-language document support
- RESTful API endpoint
- Docker Compose configuration for simplified deployment
- Database integration for large-scale cataloging

---

**Developed and maintained by [Hardik Gupta]**

For more information, visit the project repository or contact the maintainer.
