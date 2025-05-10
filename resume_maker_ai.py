#!/usr/bin/env python3
"""
Resume Maker & Optimizer
Made with ❤️ by robbie09 & lilian09

A premium desktop application for creating and optimizing resumes.
Uses CustomTkinter for a modern, crystal-clear UI.
"""
import os
import sys
import json
import logging
import requests
import threading
import re
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Configure CustomTkinter appearance
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("resume_maker.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# OpenRouter AI settings
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = "MODEL"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Application version
APP_VERSION = "1.0.0"

# ============================
# Helper Functions
# ============================

def ensure_dir(directory):
    """Ensure a directory exists, create it if not"""
    os.makedirs(directory, exist_ok=True)
    return directory

def get_output_dir():
    """Get the output directory for generated resumes"""
    output_dir = os.path.join(os.getcwd(), "output")
    ensure_dir(output_dir)
    return output_dir

# ============================
# Document Parsing Functions
# ============================

def parse_document(file_path: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Parse a document file and extract its content
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Tuple containing:
            - The document content as text
            - Optional dictionary with structured resume sections if detected
    """
    try:
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            return _parse_pdf(file_path)
        elif file_extension in ['.docx', '.doc']:
            return _parse_word(file_path)
        elif file_extension in ['.txt', '.text']:
            return _parse_text(file_path)
        else:
            logger.warning(f"Unsupported file format: {file_extension}")
            raise ValueError(f"Unsupported file format: {file_extension}")
    except Exception as e:
        logger.error(f"Error parsing document: {str(e)}")
        raise

def _parse_pdf(file_path: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Parse a PDF file and extract its content"""
    try:
        import PyPDF2
        
        text_content = ""
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"
        
        # Try to identify resume sections
        sections = _identify_resume_sections(text_content)
        
        return text_content, sections
    except Exception as e:
        logger.error(f"Error parsing PDF: {str(e)}")
        raise

def _parse_word(file_path: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Parse a Word document and extract its content"""
    try:
        import docx2txt
        
        text_content = docx2txt.process(file_path)
        
        # Try to identify resume sections
        sections = _identify_resume_sections(text_content)
        
        return text_content, sections
    except Exception as e:
        logger.error(f"Error parsing Word document: {str(e)}")
        raise

def _parse_text(file_path: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Parse a plain text file and extract its content"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text_content = file.read()
        
        # Try to identify resume sections
        sections = _identify_resume_sections(text_content)
        
        return text_content, sections
    except Exception as e:
        logger.error(f"Error parsing text file: {str(e)}")
        raise

def _identify_resume_sections(text_content: str) -> Optional[Dict[str, Any]]:
    """
    Identify common resume sections from the text content
    
    Returns:
        Dictionary with structured resume sections if patterns are detected,
        None otherwise
    """
    try:
        # Simple rule-based section detection (can be improved with AI in future)
        sections = {}
        
        # Look for common section headers using regex
        summary_pattern = r"(?i)(SUMMARY|PROFESSIONAL\s+SUMMARY|PROFILE|OBJECTIVE)[:\s]*\n(.*?)(?=\n\s*\n|\n[A-Z]+[:\s]*\n|$)"
        experience_pattern = r"(?i)(EXPERIENCE|WORK\s+EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|EMPLOYMENT)[:\s]*\n(.*?)(?=\n\s*\n|\n[A-Z]+[:\s]*\n|$)"
        education_pattern = r"(?i)(EDUCATION|ACADEMIC\s+BACKGROUND|QUALIFICATIONS)[:\s]*\n(.*?)(?=\n\s*\n|\n[A-Z]+[:\s]*\n|$)"
        skills_pattern = r"(?i)(SKILLS|TECHNICAL\s+SKILLS|CORE\s+COMPETENCIES|AREAS\s+OF\s+EXPERTISE)[:\s]*\n(.*?)(?=\n\s*\n|\n[A-Z]+[:\s]*\n|$)"
        
        # Replace multiple newlines with double newline for better regex pattern matching
        clean_text = re.sub(r'\n+', '\n\n', text_content)
        
        # Find sections
        summary_match = re.search(summary_pattern, clean_text, re.DOTALL)
        if summary_match:
            sections["summary"] = summary_match.group(2).strip()
        
        experience_match = re.search(experience_pattern, clean_text, re.DOTALL)
        if experience_match:
            sections["experience"] = experience_match.group(2).strip()
        
        education_match = re.search(education_pattern, clean_text, re.DOTALL)
        if education_match:
            sections["education"] = education_match.group(2).strip()
        
        skills_match = re.search(skills_pattern, clean_text, re.DOTALL)
        if skills_match:
            sections["skills"] = skills_match.group(2).strip()
        
        return sections if sections else None
    except Exception as e:
        logger.error(f"Error identifying resume sections: {str(e)}")
        return None

# ============================
# Document Generation Functions
# ============================

def generate_text_resume(resume_content: Dict[str, Any], output_path: str) -> str:
    """
    Generate a plain text resume document
    
    Args:
        resume_content: Dictionary containing resume content by section
        output_path: Path to save the generated text file
        
    Returns:
        Path to the generated text file
    """
    try:
        # Create nicely formatted text resume
        text_output = ""
        
        # Add resume sections in order
        if isinstance(resume_content, dict):
            for section_title, content in resume_content.items():
                if content and section_title != "suggestions" and section_title != "improvements":
                    text_output += f"{section_title.upper()}\n"
                    text_output += "-" * 20 + "\n"
                    text_output += content + "\n\n"
        
        # Add attribution
        text_output += "\n" + "-" * 40 + "\n"
        text_output += "Made with ❤️ by robbie09 & lilian09"
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text_output)
        
        logger.info(f"Generated resume saved to: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error generating text resume: {str(e)}")
        raise

# ============================
# AI Functions
# ============================

def optimize_resume(resume_content: str, job_description: Optional[str] = None) -> Dict[str, Any]:
    """
    Optimize a resume using OpenRouter AI
    
    Args:
        resume_content: The current resume content as text
        job_description: Optional job description to tailor the resume
        
    Returns:
        Dict containing the optimized resume content and suggestions
    """
    try:
        # Build prompt for the API
        prompt = _build_optimization_prompt(resume_content, job_description)
        
        # Make API request
        response = _make_api_request(prompt)
        
        # Process the response
        result = _process_optimization_response(response)
        
        return result
    except Exception as e:
        logger.error(f"Error optimizing resume: {str(e)}")
        raise

def generate_resume_from_info(user_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a complete resume from user-provided information
    
    Args:
        user_info: Dictionary containing user information sections
        
    Returns:
        Dict containing the generated resume content
    """
    try:
        # Build prompt for the API
        prompt = _build_generation_prompt(user_info)
        
        # Make API request
        response = _make_api_request(prompt)
        
        # Process the response
        result = _process_generation_response(response)
        
        return result
    except Exception as e:
        logger.error(f"Error generating resume: {str(e)}")
        raise

def _make_api_request(prompt: str) -> Dict[str, Any]:
    """
    Make a request to the OpenRouter API
    
    Args:
        prompt: The prompt to send to the API
        
    Returns:
        The API response as a dictionary
    """
    if not OPENROUTER_API_KEY:
        raise ValueError("OpenRouter API key is not set")
    
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENROUTER_API_KEY}"
        }
        
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": "You are a professional resume writer with expertise in creating and optimizing resumes."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 3000
        }
        
        logger.info(f"Making API request to OpenRouter using model: {OPENROUTER_MODEL}")
        response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60  # Set timeout to 60 seconds
        )
        
        if response.status_code != 200:
            logger.error(f"API request failed: {response.status_code} - {response.text}")
            raise ValueError(f"API request failed: {response.status_code} - {response.text}")
        
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error making API request: {str(e)}")
        raise

def _build_optimization_prompt(resume_content: str, job_description: Optional[str] = None) -> str:
    """Build the prompt for resume optimization"""
    prompt = "Please optimize and improve the following resume:"
    prompt += f"\n\n{resume_content}\n\n"
    
    if job_description:
        prompt += f"Please tailor this resume to the following job description:\n\n{job_description}\n\n"
    
    prompt += """
    Please provide the result in the following format:
    
    - First, provide the complete optimized resume content.
    - Then, list the key improvements made.
    - Finally, give 3-5 additional suggestions for further improvement.
    
    Optimize for clarity, impact, quantification of achievements, and professional language.
    Remove any fluff, use action verbs, and ensure the resume is concise but comprehensive.
    
    Format your response as JSON with the following structure:
    {
        "optimized_content": "The full optimized resume text",
        "improvements": ["List of specific improvements made"],
        "suggestions": ["List of additional suggestions"]
    }
    """
    
    return prompt

def _build_generation_prompt(user_info: Dict[str, Any]) -> str:
    """Build the prompt for resume generation from user info"""
    # Extract user information
    contact = user_info.get("contact", {})
    name = contact.get("name", "")
    email = contact.get("email", "")
    phone = contact.get("phone", "")
    location = contact.get("location", "")
    
    summary = user_info.get("summary", "")
    experience = user_info.get("experience", "")
    education = user_info.get("education", "")
    skills = user_info.get("skills", "")
    additional = user_info.get("additional", "")
    
    # Get style preferences if available
    style_info = user_info.get("style", "")
    if isinstance(style_info, str) and style_info:
        try:
            style = json.loads(style_info)
        except:
            style = {}
    else:
        style = {}
    
    layout = style.get("layout", "Traditional")
    length = style.get("length", "1-page")
    tone = style.get("tone", "Professional")
    focus = style.get("focus", "Experience")
    auto_summary = style.get("auto_summary", True)
    auto_skills = style.get("auto_skills", True)
    
    # For target job
    target_job = user_info.get("target_job", "")
    
    # Build the prompt
    prompt = f"""
    Please create a professional resume for {name} with the following information:
    
    CONTACT INFORMATION:
    Name: {name}
    Email: {email}
    Phone: {phone}
    Location: {location}
    
    PROFESSIONAL SUMMARY:
    {summary}
    
    WORK EXPERIENCE:
    {experience}
    
    EDUCATION:
    {education}
    
    SKILLS:
    {skills}
    
    ADDITIONAL INFORMATION:
    {additional}
    """
    
    if target_job:
        prompt += f"\nTARGET JOB/ROLE: {target_job}\n"
    
    # Add style guidance
    prompt += f"""
    STYLE PREFERENCES:
    - Layout: {layout}
    - Length: {length}
    - Tone: {tone}
    - Focus: {focus}
    """
    
    if auto_summary:
        prompt += "- Please enhance and polish the professional summary.\n"
    
    if auto_skills:
        prompt += "- Please organize and categorize skills for better presentation.\n"
    
    # Request format
    prompt += """
    Please provide the result as a complete, ready-to-use professional resume.
    Use clear section headings, bullet points where appropriate, and professional formatting.
    Quantify achievements where possible and use action verbs.
    
    Format your response as JSON with the following structure:
    {
        "content": {
            "summary": "Enhanced professional summary",
            "experience": "Formatted work experience section",
            "education": "Formatted education section",
            "skills": "Organized skills section",
            "additional": "Any additional information formatted appropriately"
        }
    }
    """
    
    return prompt

def _process_optimization_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Process the API response for resume optimization"""
    try:
        content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        # Extract JSON from content (handling potential text before/after JSON)
        json_match = re.search(r'({.*})', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            try:
                result = json.loads(json_str)
                return result
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in response: {json_str}")
                # Return a fallback response
                return {
                    "optimized_content": content,
                    "improvements": ["AI-generated optimization"],
                    "suggestions": ["Review the optimized resume carefully"]
                }
        
        return {
                "optimized_content": content,
                "improvements": ["AI-generated optimization"],
                "suggestions": ["Review the optimized resume carefully"]
            }
        
    except Exception as e:
        logger.error(f"Error processing optimization response: {str(e)}")
        # Return a fallback response
        return {
            "optimized_content": "Error processing AI response. Please try again.",
            "improvements": [],
            "suggestions": ["The AI service encountered an issue. Please try again."]
        }

def _process_generation_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Process the API response for resume generation"""
    try:
        content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        # Extract JSON from content (handling potential text before/after JSON)
        json_match = re.search(r'({.*})', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            try:
                result = json.loads(json_str)
                # If result has 'content' field as expected
                if 'content' in result:
                    return result['content']
                return result
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in response: {json_str}")
                # Return a structured response from the raw text
                return {
                    "summary": "Professional Summary (AI-generated)",
                    "experience": content,
                    "education": "",
                    "skills": "",
                    "additional": "Review and edit this AI-generated content."
                }
        
        # If no JSON found, return the raw content structured
        return {
            "summary": "Professional Summary (AI-generated)",
            "experience": content,
            "education": "",
            "skills": "",
            "additional": "Review and edit this AI-generated content."
        }
        
    except Exception as e:
        logger.error(f"Error processing generation response: {str(e)}")
        # Return a fallback response
        return {
            "summary": "Error processing AI response. Please try again.",
            "experience": "",
            "education": "",
            "skills": "",
            "additional": "The AI service encountered an issue. Please try again."
        }

# ============================
# Main Application Class
# ============================

class ResumeMakerApp(ctk.CTk):
    """Main application window for the Resume Maker"""
    
    def __init__(self):
        super().__init__()
        
        # Set window properties
        self.title("Resume Maker & Optimizer")
        self.geometry("1000x800")
        self.minsize(800, 600)
        
        # Try to set icon if available
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.svg")
            self.iconbitmap(icon_path)
        except Exception as e:
            logger.warning(f"Could not set application icon: {str(e)}")
        
        # Set up grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Create UI components
        self._create_ui()
        
        # Check if API key is set
        self._check_api_key()
    
    def _create_ui(self):
        """Create the UI components"""
        # Create header
        self._create_header()
        
        # Create tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        # Configure tabs
        self.tabview.add("Welcome")
        self.tabview.add("Create Resume")
        self.tabview.add("Optimize Resume")
        self.tabview.add("Preview")
        
        # Create tab content
        self._create_welcome_tab()
        self._create_create_tab()
        self._create_optimize_tab()
        self._create_preview_tab()
        
        # Set default tab
        self.tabview.set("Welcome")
        
        # Create footer
        self._create_footer()
        
        # Connect tab change event
        self.tabview.configure(command=self._on_tab_changed)
    
    def _create_header(self):
        """Create the application header"""
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        # App title
        title_label = ctk.CTkLabel(
            header_frame,
            text="Resume Maker & Optimizer",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")
        
        # Version label
        version_label = ctk.CTkLabel(
            header_frame,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=12),
            text_color=("gray60", "gray40")
        )
        version_label.grid(row=0, column=1, padx=5, pady=10, sticky="e")
    
    def _create_footer(self):
        """Create the application footer"""
        footer_frame = ctk.CTkFrame(self)
        footer_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        # Status label
        self.status_label = ctk.CTkLabel(
            footer_frame,
            text="Ready",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray70")
        )
        self.status_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")
        
        # Credits
        credits_label = ctk.CTkLabel(
            footer_frame,
            text="Made with ❤️ by robbie09 & lilian09",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("gray50", "gray70")
        )
        credits_label.grid(row=0, column=1, padx=20, pady=10, sticky="e")
    
    def _create_welcome_tab(self):
        """Create welcome tab content"""
        welcome_frame = self.tabview.tab("Welcome")
        
        # Welcome content
        welcome_label = ctk.CTkLabel(
            welcome_frame,
            text="Welcome to Resume Maker & Optimizer",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        welcome_label.pack(pady=30)
        
        info_text = """
        This application helps you create professional resumes and optimize existing ones.
        
        Choose an option below to get started:
        """
        
        info_label = ctk.CTkLabel(
            welcome_frame,
            text=info_text,
            font=ctk.CTkFont(size=14),
            justify="center"
        )
        info_label.pack(pady=20)
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(welcome_frame)
        buttons_frame.pack(pady=30)
        
        # Create Resume button
        create_button = ctk.CTkButton(
            buttons_frame,
            text="Create New Resume",
            font=ctk.CTkFont(size=14),
            width=200,
            height=40,
            command=lambda: self.tabview.set("Create Resume")
        )
        create_button.grid(row=0, column=0, padx=20, pady=20)
        
        # Optimize Resume button
        optimize_button = ctk.CTkButton(
            buttons_frame,
            text="Optimize Existing Resume",
            font=ctk.CTkFont(size=14),
            width=200,
            height=40,
            command=lambda: self.tabview.set("Optimize Resume")
        )
        optimize_button.grid(row=0, column=1, padx=20, pady=20)
        
        # Credits and attribution
        api_frame = ctk.CTkFrame(welcome_frame)
        api_frame.pack(padx=20, pady=(20, 10), fill="x")
        
        api_label = ctk.CTkLabel(
            api_frame,
            text="Made with ❤️ by robbie09 & lilian09",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("gray50", "gray70")
        )
        api_label.pack()
        
        api_link_label = ctk.CTkLabel(
            api_frame,
            text="Get an API key from OpenRouter",
            font=ctk.CTkFont(size=12, underline=True),
            text_color=("blue", "light blue"),
            cursor="hand2"
        )
        api_link_label.pack(pady=5)
        api_link_label.bind("<Button-1>", lambda e: self._open_url("https://openrouter.ai"))
    
    def _create_create_tab(self):
        """Create the Create Resume tab content"""
        create_frame = self.tabview.tab("Create Resume")
        
        # Configure grid layout
        create_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(
            create_frame,
            text="Create a New Resume",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Scrollable form frame
        form_frame = ScrollableFrame(create_frame)
        form_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        create_frame.grid_rowconfigure(1, weight=1)
        
        # Form sections
        current_row = 0
        
        # Contact Information
        current_row = self._create_section_header(form_frame, "Contact Information", current_row)
        
        # Name
        ctk.CTkLabel(form_frame, text="Full Name:").grid(row=current_row, column=0, padx=20, pady=(10, 0), sticky="w")
        self.name_entry = ctk.CTkEntry(form_frame, width=400)
        self.name_entry.grid(row=current_row, column=1, padx=20, pady=(10, 0), sticky="w")
        current_row += 1
        
        # Email
        ctk.CTkLabel(form_frame, text="Email:").grid(row=current_row, column=0, padx=20, pady=(10, 0), sticky="w")
        self.email_entry = ctk.CTkEntry(form_frame, width=400)
        self.email_entry.grid(row=current_row, column=1, padx=20, pady=(10, 0), sticky="w")
        current_row += 1
        
        # Phone
        ctk.CTkLabel(form_frame, text="Phone:").grid(row=current_row, column=0, padx=20, pady=(10, 0), sticky="w")
        self.phone_entry = ctk.CTkEntry(form_frame, width=400)
        self.phone_entry.grid(row=current_row, column=1, padx=20, pady=(10, 0), sticky="w")
        current_row += 1
        
        # Location
        ctk.CTkLabel(form_frame, text="Location:").grid(row=current_row, column=0, padx=20, pady=(10, 0), sticky="w")
        self.location_entry = ctk.CTkEntry(form_frame, width=400)
        self.location_entry.grid(row=current_row, column=1, padx=20, pady=(10, 0), sticky="w")
        current_row += 1
        
        # Professional Summary
        current_row = self._create_section_header(form_frame, "Professional Summary", current_row)
        
        # Summary text
        ctk.CTkLabel(form_frame, text="Brief overview of your experience and skills:").grid(
            row=current_row, column=0, columnspan=2, padx=20, pady=(10, 0), sticky="w"
        )
        current_row += 1
        
        self.summary_text = CTkRichTextBox(
            form_frame, 
            width=660, 
            height=100,
            placeholder_text="Enter your professional summary..."
        )
        self.summary_text.grid(row=current_row, column=0, columnspan=2, padx=20, pady=(5, 10), sticky="ew")
        current_row += 1
        
        # Work Experience
        current_row = self._create_section_header(form_frame, "Work Experience", current_row)
        
        # Experience text
        ctk.CTkLabel(form_frame, text="List your work history in reverse chronological order:").grid(
            row=current_row, column=0, columnspan=2, padx=20, pady=(10, 0), sticky="w"
        )
        current_row += 1
        
        self.experience_text = CTkRichTextBox(
            form_frame, 
            width=660, 
            height=150,
            placeholder_text="Enter your work experience...\n\nExample:\nSoftware Engineer | ABC Company | Jan 2020 - Present\n- Developed and maintained web applications\n- Collaborated with cross-functional teams"
        )
        self.experience_text.grid(row=current_row, column=0, columnspan=2, padx=20, pady=(5, 10), sticky="ew")
        current_row += 1
        
        # Education
        current_row = self._create_section_header(form_frame, "Education", current_row)
        
        # Education text
        ctk.CTkLabel(form_frame, text="List your educational background:").grid(
            row=current_row, column=0, columnspan=2, padx=20, pady=(10, 0), sticky="w"
        )
        current_row += 1
        
        self.education_text = CTkRichTextBox(
            form_frame, 
            width=660, 
            height=100,
            placeholder_text="Enter your education details...\n\nExample:\nBachelor of Science in Computer Science | XYZ University | 2016-2020\n- GPA: 3.8/4.0\n- Relevant coursework: Data Structures, Algorithms"
        )
        self.education_text.grid(row=current_row, column=0, columnspan=2, padx=20, pady=(5, 10), sticky="ew")
        current_row += 1
        
        # Skills
        current_row = self._create_section_header(form_frame, "Skills", current_row)
        
        # Skills text
        ctk.CTkLabel(form_frame, text="List your technical and soft skills:").grid(
            row=current_row, column=0, columnspan=2, padx=20, pady=(10, 0), sticky="w"
        )
        current_row += 1
        
        self.skills_text = CTkRichTextBox(
            form_frame, 
            width=660, 
            height=100,
            placeholder_text="Enter your skills...\n\nExample:\nTechnical: Python, JavaScript, React, SQL\nSoft Skills: Team collaboration, Problem-solving, Communication"
        )
        self.skills_text.grid(row=current_row, column=0, columnspan=2, padx=20, pady=(5, 10), sticky="ew")
        current_row += 1
        
        # Additional Information
        current_row = self._create_section_header(form_frame, "Additional Information (Optional)", current_row)
        
        # Additional text
        ctk.CTkLabel(form_frame, text="Any other relevant information (certifications, projects, languages):").grid(
            row=current_row, column=0, columnspan=2, padx=20, pady=(10, 0), sticky="w"
        )
        current_row += 1
        
        self.additional_text = CTkRichTextBox(
            form_frame, 
            width=660, 
            height=100,
            placeholder_text="Enter additional information...\n\nExample:\n- AWS Certified Developer\n- Fluent in English and Spanish\n- GitHub: github.com/yourusername"
        )
        self.additional_text.grid(row=current_row, column=0, columnspan=2, padx=20, pady=(5, 10), sticky="ew")
        current_row += 1
        
        # Target Job/Role
        current_row = self._create_section_header(form_frame, "Target Job (Optional)", current_row)
        
        # Target text
        ctk.CTkLabel(form_frame, text="Specific job or role you're targeting (helps tailor the resume):").grid(
            row=current_row, column=0, columnspan=2, padx=20, pady=(10, 0), sticky="w"
        )
        current_row += 1
        
        self.target_text = CTkRichTextBox(
            form_frame, 
            width=660, 
            height=60,
            placeholder_text="Enter target job details...\n\nExample: Senior Software Engineer specializing in cloud infrastructure and DevOps"
        )
        self.target_text.grid(row=current_row, column=0, columnspan=2, padx=20, pady=(5, 10), sticky="ew")
        current_row += 1
        
        # Style Options
        current_row = self._create_section_header(form_frame, "Style Options", current_row)
        
        # Style options frame
        style_frame = ctk.CTkFrame(form_frame)
        style_frame.grid(row=current_row, column=0, columnspan=2, padx=20, pady=(10, 20), sticky="ew")
        current_row += 1
        
        # Layout
        ctk.CTkLabel(style_frame, text="Layout:").grid(row=0, column=0, padx=20, pady=10, sticky="w")
        self.style_option = ctk.CTkOptionMenu(
            style_frame,
            values=["Traditional", "Modern", "Creative", "Simple"],
            width=150
        )
        self.style_option.grid(row=0, column=1, padx=5, pady=10, sticky="w")
        self.style_option.set("Traditional")
        
        # Length
        ctk.CTkLabel(style_frame, text="Length:").grid(row=0, column=2, padx=20, pady=10, sticky="w")
        self.length_option = ctk.CTkOptionMenu(
            style_frame,
            values=["1-page", "2-page", "Concise", "Detailed"],
            width=150
        )
        self.length_option.grid(row=0, column=3, padx=5, pady=10, sticky="w")
        self.length_option.set("1-page")
        
        # Tone
        ctk.CTkLabel(style_frame, text="Tone:").grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.tone_option = ctk.CTkOptionMenu(
            style_frame,
            values=["Professional", "Confident", "Achievement-focused", "Technical"],
            width=150
        )
        self.tone_option.grid(row=1, column=1, padx=5, pady=10, sticky="w")
        self.tone_option.set("Professional")
        
        # Focus
        ctk.CTkLabel(style_frame, text="Focus:").grid(row=1, column=2, padx=20, pady=10, sticky="w")
        self.focus_option = ctk.CTkOptionMenu(
            style_frame,
            values=["Experience", "Skills", "Education", "Balanced"],
            width=150
        )
        self.focus_option.grid(row=1, column=3, padx=5, pady=10, sticky="w")
        self.focus_option.set("Experience")
        
        # Checkbox options
        self.auto_summary_var = ctk.BooleanVar(value=True)
        auto_summary_cb = ctk.CTkCheckBox(
            style_frame,
            text="Enhance professional summary",
            variable=self.auto_summary_var
        )
        auto_summary_cb.grid(row=2, column=0, columnspan=2, padx=20, pady=10, sticky="w")
        
        self.auto_skills_var = ctk.BooleanVar(value=True)
        auto_skills_cb = ctk.CTkCheckBox(
            style_frame,
            text="Organize and categorize skills",
            variable=self.auto_skills_var
        )
        auto_skills_cb.grid(row=2, column=2, columnspan=2, padx=20, pady=10, sticky="w")
        
        # Preview button
        preview_button = ctk.CTkButton(
            create_frame,
            text="Preview Resume",
            font=ctk.CTkFont(size=14),
            width=200,
            height=40,
            command=self._preview_create
        )
        preview_button.grid(row=2, column=0, padx=20, pady=20)
        
        # Generate button
        generate_button = ctk.CTkButton(
            create_frame,
            text="Generate Resume with AI",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("green", "dark green"),
            hover_color=("dark green", "green"),
            width=200,
            height=40,
            command=self._generate_resume
        )
        generate_button.grid(row=3, column=0, padx=20, pady=(0, 20))
    
    def _create_optimize_tab(self):
        """Create the Optimize Resume tab content"""
        optimize_frame = self.tabview.tab("Optimize Resume")
        
        # Configure grid layout
        optimize_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(
            optimize_frame,
            text="Optimize an Existing Resume",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Instructions
        instructions_label = ctk.CTkLabel(
            optimize_frame,
            text="Upload your existing resume file and optionally paste a job description to tailor it.",
            font=ctk.CTkFont(size=14)
        )
        instructions_label.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
        
        # Upload frame
        upload_frame = ctk.CTkFrame(optimize_frame)
        upload_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        # Upload button
        upload_button = ctk.CTkButton(
            upload_frame,
            text="Upload Resume File",
            font=ctk.CTkFont(size=14),
            width=200,
            height=40,
            command=self._upload_resume
        )
        upload_button.grid(row=0, column=0, padx=20, pady=20)
        
        # File info
        self.file_label = ctk.CTkLabel(
            upload_frame,
            text="No file selected",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray70")
        )
        self.file_label.grid(row=0, column=1, padx=20, pady=20, sticky="w")
        
        # Job description frame
        job_frame = ctk.CTkFrame(optimize_frame)
        job_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        optimize_frame.grid_rowconfigure(3, weight=1)
        
        # Job description label
        job_label = ctk.CTkLabel(
            job_frame,
            text="Job Description (Optional):",
            font=ctk.CTkFont(size=14)
        )
        job_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Job description text
        self.job_text = CTkRichTextBox(
            job_frame, 
            width=660, 
            height=200,
            placeholder_text="Paste the job description here to tailor your resume...\n\nThe AI will optimize your resume to highlight relevant skills and experiences for this specific job."
        )
        self.job_text.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        job_frame.grid_columnconfigure(0, weight=1)
        
        # Preview button
        preview_button = ctk.CTkButton(
            optimize_frame,
            text="Preview Resume",
            font=ctk.CTkFont(size=14),
            width=200,
            height=40,
            command=self._preview_optimize,
            state="disabled"
        )
        preview_button.grid(row=4, column=0, padx=20, pady=10)
        self.preview_optimize_button = preview_button
        
        # Optimize button
        optimize_button = ctk.CTkButton(
            optimize_frame,
            text="Optimize Resume with AI",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("green", "dark green"),
            hover_color=("dark green", "green"),
            width=200,
            height=40,
            command=self._optimize_resume,
            state="disabled"
        )
        optimize_button.grid(row=5, column=0, padx=20, pady=(0, 20))
        self.optimize_button = optimize_button
    
    def _create_preview_tab(self):
        """Create the Preview tab content"""
        preview_frame = self.tabview.tab("Preview")
        
        # Configure grid layout
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(2, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(
            preview_frame,
            text="Resume Preview",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Controls frame
        controls_frame = ctk.CTkFrame(preview_frame)
        controls_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        # Font size control
        ctk.CTkLabel(controls_frame, text="Font Size:").grid(row=0, column=0, padx=20, pady=10, sticky="w")
        self.font_size = ctk.CTkOptionMenu(
            controls_frame,
            values=["Small", "Medium", "Large"],
            command=self._update_preview_font,
            width=150
        )
        self.font_size.grid(row=0, column=1, padx=5, pady=10, sticky="w")
        self.font_size.set("Medium")
        
        # Save button
        save_button = ctk.CTkButton(
            controls_frame,
            text="Save to File",
            font=ctk.CTkFont(size=14),
            width=150,
            height=30,
            command=self._save_preview
        )
        save_button.grid(row=0, column=2, padx=20, pady=10)
        
        # Preview text
        self.preview_text = ctk.CTkTextbox(preview_frame, height=400, font=("Courier New", 12))
        self.preview_text.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="nsew")
        self.preview_text.insert("1.0", "Resume preview will appear here.")
        self.preview_text.configure(state="disabled")
    
    def _create_section_header(self, parent, title, row):
        """Create a section header"""
        header_frame = ctk.CTkFrame(parent, fg_color=("gray85", "gray25"))
        header_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=(20, 5), sticky="ew")
        
        header_label = ctk.CTkLabel(
            header_frame,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("gray20", "gray90")
        )
        header_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        return row + 1
    
    def _on_tab_changed(self, selected_tab):
        """Handle tab change event"""
        # Update status bar
        if selected_tab == "Welcome":
            self.status_label.configure(text="Welcome to Resume Maker")
        elif selected_tab == "Create Resume":
            self.status_label.configure(text="Create a new resume from scratch")
        elif selected_tab == "Optimize Resume":
            self.status_label.configure(text="Optimize an existing resume")
        elif selected_tab == "Preview":
            self.status_label.configure(text="Preview your resume")
    
    def _upload_resume(self):
        """Handle resume upload"""
        # Open file dialog
        file_path = filedialog.askopenfilename(
            title="Select Resume File",
            filetypes=[
                ("Document Files", "*.pdf;*.docx;*.doc;*.txt"),
                ("PDF Files", "*.pdf"),
                ("Word Documents", "*.docx;*.doc"),
                ("Text Files", "*.txt")
            ]
        )
        
        if not file_path:
            return
        
        try:
            # Parse document
            self.status_label.configure(text=f"Parsing {os.path.basename(file_path)}...")
            
            # Store file path and content
            self.resume_file_path = file_path
            self.resume_content, self.resume_sections = parse_document(file_path)
            
            # Update file label
            self.file_label.configure(text=f"File: {os.path.basename(file_path)}")
            
            # Enable optimize and preview buttons
            self.optimize_button.configure(state="normal")
            self.preview_optimize_button.configure(state="normal")
            
            # Update status
            self.status_label.configure(text=f"Loaded {os.path.basename(file_path)}")
            
        except Exception as e:
            logger.error(f"Error uploading resume: {str(e)}")
            messagebox.showerror(
                "Error",
                f"Failed to upload resume:\n\n{str(e)}"
            )
    
    def _preview_create(self):
        """Preview the resume from Create tab"""
        # Validate form
        if not self._validate_create_form():
            return
        
        # Collect form data for preview
        preview_text = self._collect_form_data_as_text()
        
        # Set preview content
        self._set_preview_content(preview_text)
        
        # Switch to preview tab
        self.tabview.set("Preview")
    
    def _preview_optimize(self):
        """Preview the resume from Optimize tab"""
        if not hasattr(self, 'resume_content'):
            messagebox.showwarning(
                "No Resume",
                "Please upload a resume file first."
            )
            return
        
        # Set preview content
        self._set_preview_content(self.resume_content)
        
        # Switch to preview tab
        self.tabview.set("Preview")
    
    def _generate_resume(self):
        """Generate a resume with AI"""
        # Validate form
        if not self._validate_create_form():
            return
        
        # Show API key warning if not set
        if not OPENROUTER_API_KEY:
            self._show_api_key_missing()
            return
        
        # Show progress dialog
        progress = ctk.CTkToplevel(self)
        progress.title("Generating Resume")
        progress.geometry("300x120")
        progress.resizable(False, False)
        progress.transient(self)
        progress.grab_set()
        
        # Center progress dialog
        progress.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - progress.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - progress.winfo_height()) // 2
        progress.geometry(f"+{x}+{y}")
        
        # Progress message
        ctk.CTkLabel(
            progress,
            text="Generating resume using AI...",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(20, 10))
        
        ctk.CTkLabel(
            progress,
            text="This may take up to 30 seconds.",
            font=ctk.CTkFont(size=12)
        ).pack(pady=(0, 10))
        
        # Define generation thread
        def generate_thread():
            try:
                # Collect user info
                user_info = self._collect_user_info()
                
                # Generate resume
                result = generate_resume_from_info(user_info)
                
                # Generate output file
                output_dir = get_output_dir()
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = os.path.join(output_dir, f"Generated_Resume_{timestamp}.txt")
                
                generate_text_resume(result, output_path)
                
                # Update UI from main thread
                self.after(100, lambda: self._generation_complete(result, output_path=output_path))
                
            except Exception as e:
                logger.error(f"Error generating resume: {str(e)}")
                self.after(100, lambda: messagebox.showerror(
                    "Error Generating Resume",
                    f"Failed to generate resume:\n\n{str(e)}"
                ))
                
            finally:
                # Close progress dialog
                self.after(100, lambda: progress.destroy())
        
        # Start thread
        threading.Thread(target=generate_thread, daemon=True).start()
    
    def _optimize_resume(self):
        """Optimize a resume with AI"""
        if not hasattr(self, 'resume_content'):
            messagebox.showwarning(
                "No Resume",
                "Please upload a resume file first."
            )
            return
        
        # Show API key warning if not set
        if not OPENROUTER_API_KEY:
            self._show_api_key_missing()
            return
        
        # Get job description (if any)
        job_description = self.job_text.get_content()
        
        # Show progress dialog
        progress = ctk.CTkToplevel(self)
        progress.title("Optimizing Resume")
        progress.geometry("300x120")
        progress.resizable(False, False)
        progress.transient(self)
        progress.grab_set()
        
        # Center progress dialog
        progress.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - progress.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - progress.winfo_height()) // 2
        progress.geometry(f"+{x}+{y}")
        
        # Progress message
        ctk.CTkLabel(
            progress,
            text="Optimizing resume using AI...",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(20, 10))
        
        ctk.CTkLabel(
            progress,
            text="This may take up to 30 seconds.",
            font=ctk.CTkFont(size=12)
        ).pack(pady=(0, 10))
        
        # Define optimize thread
        def optimize_thread():
            try:
                # Optimize resume
                result = optimize_resume(self.resume_content, job_description)
                
                # Generate output file
                output_dir = get_output_dir()
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = os.path.join(output_dir, f"Optimized_Resume_{timestamp}.txt")
                
                generate_text_resume(result, output_path)
                
                # Update UI from main thread
                self.after(100, lambda: self._optimization_complete(result, output_path=output_path))
                
            except Exception as e:
                logger.error(f"Error optimizing resume: {str(e)}")
                self.after(100, lambda: messagebox.showerror(
                    "Error Optimizing Resume",
                    f"Failed to optimize resume:\n\n{str(e)}"
                ))
                
            finally:
                # Close progress dialog
                self.after(100, lambda: progress.destroy())
        
        # Start thread
        threading.Thread(target=optimize_thread, daemon=True).start()
    
    def _save_preview(self):
        """Save the preview content to a file"""
        # Get content
        content = self.preview_text.get("1.0", "end-1c")
        
        if not content or content == "Resume preview will appear here.":
            messagebox.showwarning(
                "No Content",
                "There is no resume content to save."
            )
            return
        
        # Ask for save location
        file_path = filedialog.asksaveasfilename(
            title="Save Resume",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")]
        )
        
        if not file_path:
            return
        
        try:
            # Save file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Show success message
            messagebox.showinfo(
                "Save Successful",
                f"Resume saved to:\n{file_path}"
            )
        except Exception as e:
            logger.error(f"Error saving resume: {str(e)}")
            messagebox.showerror(
                "Error",
                f"Failed to save resume:\n\n{str(e)}"
            )
    
    def _generation_complete(self, result, output_path=None):
        """Handle resume generation completion"""
        # Check if result is valid
        if not result:
            messagebox.showerror(
                "Error",
                "Failed to generate resume. Please try again."
            )
            return
        
        # Format content for preview
        if isinstance(result, dict):
            preview_content = ""
            
            # Add sections
            for section_title, content in result.items():
                if content and section_title not in ["suggestions", "improvements"]:
                    preview_content += f"{section_title.upper()}\n"
                    preview_content += "-" * 20 + "\n"
                    preview_content += content + "\n\n"
        else:
            preview_content = str(result)
        
        # Set preview content
        self._set_preview_content(preview_content)
        
        # Show success message with path
        if output_path:
            messagebox.showinfo(
                "Resume Generated",
                f"Resume has been generated and saved to:\n{output_path}\n\nView the resume in the Preview tab."
            )
        
        # Switch to preview tab
        self.tabview.set("Preview")
    
    def _optimization_complete(self, result, output_path=None):
        """Handle resume optimization completion"""
        # Check if result is valid
        if not result:
            messagebox.showerror(
                "Error",
                "Failed to optimize resume. Please try again."
            )
            return
        
        # Format content for preview
        if isinstance(result, dict):
            preview_content = ""
            
            # Main content
            if "optimized_content" in result:
                preview_content += result["optimized_content"] + "\n\n"
            
            # Improvements
            if "improvements" in result and result["improvements"]:
                preview_content += "IMPROVEMENTS MADE\n"
                preview_content += "-" * 20 + "\n"
                for item in result["improvements"]:
                    preview_content += f"- {item}\n"
                preview_content += "\n"
            
            # Suggestions
            if "suggestions" in result and result["suggestions"]:
                preview_content += "ADDITIONAL SUGGESTIONS\n"
                preview_content += "-" * 20 + "\n"
                for item in result["suggestions"]:
                    preview_content += f"- {item}\n"
                preview_content += "\n"
        else:
            preview_content = str(result)
        
        # Set preview content
        self._set_preview_content(preview_content)
        
        # Show success message with path
        if output_path:
            messagebox.showinfo(
                "Resume Optimized",
                f"Resume has been optimized and saved to:\n{output_path}\n\nView the resume in the Preview tab."
            )
        
        # Switch to preview tab
        self.tabview.set("Preview")
    
    def _show_progress_dialog(self, title):
        """Show a progress dialog"""
        progress = ctk.CTkToplevel(self)
        progress.title(title)
        progress.geometry("300x120")
        progress.resizable(False, False)
        progress.transient(self)
        progress.grab_set()
        
        # Center progress dialog
        progress.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - progress.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - progress.winfo_height()) // 2
        progress.geometry(f"+{x}+{y}")
        
        return progress
    
    def _set_preview_content(self, content):
        """Set the content of the preview tab"""
        # Enable editing
        self.preview_text.configure(state="normal")
        
        # Clear existing content
        self.preview_text.delete("1.0", "end")
        
        # Insert new content
        self.preview_text.insert("1.0", content)
        
        # Disable editing
        self.preview_text.configure(state="disabled")
        
        # Update font size
        self._update_preview_font()
    
    def _update_preview_font(self, value=None):
        """Update the preview font based on selected size"""
        size = self.font_size.get()
        
        if size == "Small":
            self.preview_text.configure(font=("Courier New", 10))
        elif size == "Medium":
            self.preview_text.configure(font=("Courier New", 12))
        elif size == "Large":
            self.preview_text.configure(font=("Courier New", 14))
    
    def _validate_create_form(self):
        """Validate the create resume form"""
        # Check if name is filled
        if not self.name_entry.get().strip():
            messagebox.showwarning(
                "Missing Information",
                "Please enter your name."
            )
            return False
        
        # Check if at least one contact method is provided
        if not self.email_entry.get().strip() and not self.phone_entry.get().strip():
            messagebox.showwarning(
                "Missing Information",
                "Please provide at least one contact method (email or phone)."
            )
            return False
        
        # Check if experience is provided
        if not self.experience_text.get_content().strip():
            messagebox.showwarning(
                "Missing Information",
                "Please enter your work experience."
            )
            return False
        
        # Check if education is provided
        if not self.education_text.get_content().strip():
            messagebox.showwarning(
                "Missing Information",
                "Please enter your education details."
            )
            return False
        
        return True
    
    def _collect_user_info(self):
        """Collect user information from create form"""
        # Create user info dictionary
        user_info = {}
        
        # Contact info
        user_info["contact"] = {
            "name": self.name_entry.get().strip(),
            "email": self.email_entry.get().strip(),
            "phone": self.phone_entry.get().strip(),
            "location": self.location_entry.get().strip()
        }
        
        # Sections
        user_info["summary"] = self.summary_text.get_content().strip()
        user_info["experience"] = self.experience_text.get_content().strip()
        user_info["education"] = self.education_text.get_content().strip()
        user_info["skills"] = self.skills_text.get_content().strip()
        user_info["additional"] = self.additional_text.get_content().strip()
        
        # Target job
        target_job = self.target_text.get_content()
        if target_job:
            user_info["target_job"] = target_job
        
        # Add style options as a string representation
        style_dict = {
            "layout": self.style_option.get(),
            "length": self.length_option.get(),
            "tone": self.tone_option.get(),
            "focus": self.focus_option.get(),
            "auto_summary": self.auto_summary_var.get(),
            "auto_skills": self.auto_skills_var.get()
        }
        user_info["style"] = json.dumps(style_dict)
        
        return user_info
    
    def _collect_form_data_as_text(self):
        """Collect form data as formatted text for preview"""
        # Create formatted text
        resume_text = ""
        
        # Contact info
        name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        phone = self.phone_entry.get().strip()
        location = self.location_entry.get().strip()
        
        # Header with contact info
        resume_text += f"{name.upper()}\n"
        contact_info = []
        if email:
            contact_info.append(f"Email: {email}")
        if phone:
            contact_info.append(f"Phone: {phone}")
        if location:
            contact_info.append(f"Location: {location}")
        
        resume_text += " | ".join(contact_info) + "\n\n"
        
        # Summary
        summary = self.summary_text.get_content().strip()
        if summary:
            resume_text += "PROFESSIONAL SUMMARY\n"
            resume_text += "-" * 20 + "\n"
            resume_text += summary + "\n\n"
        
        # Experience
        experience = self.experience_text.get_content().strip()
        if experience:
            resume_text += "EXPERIENCE\n"
            resume_text += "-" * 20 + "\n"
            resume_text += experience + "\n\n"
        
        # Education
        education = self.education_text.get_content().strip()
        if education:
            resume_text += "EDUCATION\n"
            resume_text += "-" * 20 + "\n"
            resume_text += education + "\n\n"
        
        # Skills
        skills = self.skills_text.get_content().strip()
        if skills:
            resume_text += "SKILLS\n"
            resume_text += "-" * 20 + "\n"
            resume_text += skills + "\n\n"
        
        # Additional information
        additional = self.additional_text.get_content().strip()
        if additional:
            resume_text += "ADDITIONAL INFORMATION\n"
            resume_text += "-" * 20 + "\n"
            resume_text += additional + "\n\n"
        
        # Add note about preview
        resume_text += "\n" + "-" * 40 + "\n"
        resume_text += "PREVIEW MODE: Final resume will be formatted professionally\n"
        resume_text += "Made with ❤️ by robbie09 & lilian09"
        
        return resume_text
    
    def _check_api_key(self):
        """Check if API key is available"""
        if not OPENROUTER_API_KEY:
            self.after(1000, lambda: self._show_api_key_missing())
    
    def _show_api_key_missing(self):
        """Show warning about missing API key"""
        messagebox.showwarning(
            "API Key Missing",
            "OpenRouter API key is not set. AI features will not work.\n\n"
            "You can set it using the OPENROUTER_API_KEY environment variable.\n"
            "You can obtain a key from: https://openrouter.ai/"
        )
    
    def _open_url(self, url):
        """Open a URL in the browser"""
        import webbrowser
        try:
            webbrowser.open(url)
        except Exception:
            logger.error(f"Error opening URL: {url}")
            pass

# ============================
# Custom Widgets
# ============================

class ScrollableFrame(ctk.CTkScrollableFrame):
    """Enhanced scrollable frame with better usability"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

class CTkRichTextBox(ctk.CTkTextbox):
    """Enhanced text box with additional features"""
    
    def __init__(self, master, placeholder_text=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.placeholder_text = placeholder_text
        self.placeholder_active = False
        
        # Configure text widget
        self.configure(wrap="word")
        
        # Bind focus events
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        
        # Show placeholder initially
        if placeholder_text:
            self._show_placeholder()
    
    def _show_placeholder(self):
        """Show placeholder text"""
        self.delete("1.0", "end")
        self.insert("1.0", self.placeholder_text)
        self.configure(text_color=("gray60", "gray40"))
        self.placeholder_active = True
    
    def _on_focus_in(self, event):
        """Handle focus in event"""
        if self.placeholder_active:
            self.delete("1.0", "end")
            self.configure(text_color=("black", "white"))
            self.placeholder_active = False
    
    def _on_focus_out(self, event):
        """Handle focus out event"""
        if not self.get("1.0", "end-1c"):
            self._show_placeholder()
    
    def get_content(self):
        """Get actual content, ignoring placeholder"""
        if self.placeholder_active:
            return ""
        return self.get("1.0", "end-1c")
    
    def set_content(self, text):
        """Set content, handling placeholder"""
        self.delete("1.0", "end")
        if text:
            self.insert("1.0", text)
            self.configure(text_color=("black", "white"))
            self.placeholder_active = False
        else:
            self._show_placeholder()

# ============================
# Main Entry Point
# ============================

def main():
    app = ResumeMakerApp()
    app.mainloop()

if __name__ == "__main__":
    main()