"""
Document Processing Module for 4-plex Investment Platform
Integrates multifamily document processing capabilities with foreclosure analysis
"""

import os
import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
import json
import asyncio
import time
from datetime import datetime
import pandas as pd
import numpy as np
import hashlib
import pickle
import re

# PDF and Excel processing libraries
try:
    import pdfplumber
    import PyPDF2
    PDF_PROCESSING_AVAILABLE = True
except ImportError:
    PDF_PROCESSING_AVAILABLE = False
    logging.warning("PDF processing libraries not available. Install pdfplumber and PyPDF2.")

try:
    import openpyxl
    EXCEL_PROCESSING_AVAILABLE = True
except ImportError:
    EXCEL_PROCESSING_AVAILABLE = False
    logging.warning("Excel processing library not available. Install openpyxl.")

# AI Processing libraries
try:
    import openai
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    from langchain_community.vectorstores import FAISS
    AI_PROCESSING_AVAILABLE = True
except ImportError:
    AI_PROCESSING_AVAILABLE = False
    logging.warning("AI processing libraries not available. Basic document analysis only.")

from concurrent.futures import ThreadPoolExecutor, as_completed

from models import Property, PropertyAnalysis, FinancialMetrics, ProcessingJob
from database.connection import DatabaseManager
from financial_calculations import FinancialCalculator

class DocumentProcessor:
    """
    Advanced document processing for real estate investment analysis
    Supports foreclosure documents, rent rolls, T12 statements, offering memorandums
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseManager(config.get('database', {}))
        self.financial_calculator = FinancialCalculator(config.get('financial_assumptions', {}))
        
        # Processing configuration
        self.max_file_size_mb = config.get('processing', {}).get('max_file_size_mb', 50)
        self.enable_async = config.get('processing', {}).get('enable_async', True)
        self.max_workers = config.get('processing', {}).get('max_workers', 4)
        self.chunk_size = config.get('processing', {}).get('chunk_size', 1000)
        self.max_memory_mb = config.get('processing', {}).get('max_memory_mb', 512)
        
        # AI Configuration
        self.openai_api_key = config.get('openai_api_key')
        self.ai_enabled = AI_PROCESSING_AVAILABLE and self.openai_api_key
        
        # Caching
        self.cache_enabled = config.get('processing', {}).get('enable_caching', True)
        self.cache_ttl_hours = config.get('processing', {}).get('cache_ttl_hours', 24)
        self.cache_dir = config.get('processing', {}).get('cache_dir', '.cache')
        
        if self.cache_enabled:
            os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize AI components
        if self.ai_enabled:
            self.client = openai.OpenAI(api_key=self.openai_api_key)
            self.embeddings = OpenAIEmbeddings(api_key=self.openai_api_key)
            self.llm = ChatOpenAI(temperature=0.1, api_key=self.openai_api_key, model="gpt-3.5-turbo")
    
    async def process_property_documents(
        self,
        property_id: str,
        document_paths: Dict[str, Optional[str]],
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main processing pipeline for property documents
        Handles foreclosure documents, rent rolls, financial statements
        
        Args:
            property_id: Unique property identifier
            document_paths: Dictionary mapping document types to file paths
            job_id: Optional processing job ID for tracking
            
        Returns:
            Comprehensive analysis results with financial projections
        """
        start_time = time.time()
        
        # Create or update processing job
        if not job_id:
            job_id = f"job_{int(time.time())}"
        
        job = ProcessingJob(
            id=job_id,
            property_id=property_id,
            status="processing",
            created_at=datetime.now(),
            progress=0,
            metadata={
                "document_types": list(document_paths.keys()),
                "total_files": len([p for p in document_paths.values() if p])
            }
        )
        self.db_manager.save_job(job.dict())
        
        try:
            # Initialize results structure
            results = {
                'property_id': property_id,
                'job_id': job_id,
                'document_analysis': {},
                'financial_analysis': {},
                'investment_metrics': {},
                'risk_assessment': {},
                'recommendations': {},
                'metadata': {
                    'processing_start': datetime.now().isoformat(),
                    'files_processed': [],
                    'processing_errors': [],
                    'validation_errors': [],
                    'ai_enabled': self.ai_enabled
                }
            }
            
            # Update progress
            job.progress = 10
            self.db_manager.update_job_status(job_id, "processing", 10)
            
            # Step 1: Document Processing
            self.logger.info(f"Starting document processing for property {property_id}")
            document_data = await self._process_documents_with_validation(document_paths)
            results['document_analysis'] = document_data
            results['metadata']['files_processed'] = document_data.get('metadata', {}).get('files_processed', [])
            
            # Update progress
            job.progress = 40
            self.db_manager.update_job_status(job_id, "processing", 40)
            
            # Step 2: Financial Analysis
            self.logger.info("Performing financial analysis")
            financial_analysis = await self._perform_financial_analysis(document_data)
            results['financial_analysis'] = financial_analysis
            
            # Update progress
            job.progress = 60
            self.db_manager.update_job_status(job_id, "processing", 60)
            
            # Step 3: Investment Analysis
            self.logger.info("Calculating investment metrics")
            investment_metrics = await self._calculate_investment_metrics(document_data, financial_analysis)
            results['investment_metrics'] = investment_metrics
            
            # Update progress  
            job.progress = 80
            self.db_manager.update_job_status(job_id, "processing", 80)
            
            # Step 4: AI Analysis (if enabled)
            if self.ai_enabled:
                self.logger.info("Performing AI analysis")
                ai_analysis = await self._perform_ai_analysis(document_data, financial_analysis)
                results['ai_insights'] = ai_analysis
                results['risk_assessment'] = ai_analysis.get('risk_assessment', {})
                results['recommendations'] = ai_analysis.get('recommendations', {})
            else:
                # Basic rule-based analysis
                results['risk_assessment'] = self._basic_risk_assessment(investment_metrics)
                results['recommendations'] = self._basic_recommendations(investment_metrics)
            
            # Step 5: Generate Property Analysis
            property_analysis = self._create_property_analysis(property_id, results)
            saved_analysis = self.db_manager.save_analysis(property_analysis.dict())
            results['analysis_id'] = saved_analysis.get('id')
            
            # Update completion
            results['metadata']['processing_time_seconds'] = time.time() - start_time
            results['metadata']['processing_end'] = datetime.now().isoformat()
            
            # Complete job
            job.progress = 100
            job.status = "completed"
            job.results = results
            self.db_manager.update_job_status(job_id, "completed", 100, results)
            
            self.logger.info(f"Document processing completed for property {property_id} in {time.time() - start_time:.1f}s")
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing documents for property {property_id}: {str(e)}")
            
            # Update job with error
            job.status = "failed"
            job.error_message = str(e)
            self.db_manager.update_job_status(job_id, "failed", job.progress, error=str(e))
            
            raise
    
    async def _process_documents_with_validation(self, document_paths: Dict[str, Optional[str]]) -> Dict[str, Any]:
        """Process and validate all provided documents"""
        
        # Validate all files first
        valid_files = {}
        validation_errors = []
        
        for doc_type, file_path in document_paths.items():
            if file_path and os.path.exists(file_path):
                validation = self.validate_file(file_path)
                if validation['valid']:
                    valid_files[doc_type] = file_path
                    self.logger.info(f"File validation passed for {doc_type}: {validation['size_mb']:.1f}MB")
                else:
                    error_msg = f"Validation failed for {doc_type}: {validation['error']}"
                    self.logger.error(error_msg)
                    validation_errors.append(error_msg)
        
        if not valid_files:
            raise ValueError("No valid documents found for processing")
        
        # Process documents based on type
        processed_documents = {}
        
        if self.enable_async and len(valid_files) > 1:
            # Parallel processing for multiple files
            processed_documents = await self._process_documents_async(valid_files)
        else:
            # Sequential processing
            processed_documents = self._process_documents_sync(valid_files)
        
        # Add validation errors to metadata
        if 'metadata' not in processed_documents:
            processed_documents['metadata'] = {}
        processed_documents['metadata']['validation_errors'] = validation_errors
        
        return processed_documents
    
    async def _process_documents_async(self, valid_files: Dict[str, str]) -> Dict[str, Any]:
        """Process documents asynchronously"""
        
        results = {
            'foreclosure_docs': [],
            'rent_roll': None,
            't12': None,
            'offering_memo': None,
            'property_docs': [],
            'metadata': {
                'files_processed': [],
                'processing_errors': [],
                'async_processing': True
            }
        }
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_type = {}
            
            for doc_type, file_path in valid_files.items():
                if doc_type in ['foreclosure', 'notice', 'deed', 'lien']:
                    future = executor.submit(self._process_foreclosure_document, file_path, doc_type)
                elif doc_type == 'rent_roll':
                    future = executor.submit(self._process_rent_roll, file_path)
                elif doc_type == 't12':
                    future = executor.submit(self._process_t12, file_path)
                elif doc_type == 'offering_memo':
                    future = executor.submit(self._process_offering_memo, file_path)
                else:
                    future = executor.submit(self._process_generic_property_doc, file_path, doc_type)
                
                future_to_type[future] = (doc_type, file_path)
            
            # Collect results
            for future in as_completed(future_to_type):
                doc_type, file_path = future_to_type[future]
                try:
                    result = future.result()
                    
                    if doc_type in ['foreclosure', 'notice', 'deed', 'lien']:
                        results['foreclosure_docs'].append(result)
                    elif doc_type == 'rent_roll':
                        results['rent_roll'] = result
                    elif doc_type == 't12':
                        results['t12'] = result
                    elif doc_type == 'offering_memo':
                        results['offering_memo'] = result
                    else:
                        results['property_docs'].append(result)
                    
                    results['metadata']['files_processed'].append(doc_type)
                    self.logger.info(f"{doc_type} processed successfully")
                    
                except Exception as e:
                    error_msg = f"Error processing {doc_type}: {str(e)}"
                    self.logger.error(error_msg)
                    results['metadata']['processing_errors'].append(error_msg)
        
        return results
    
    def _process_documents_sync(self, valid_files: Dict[str, str]) -> Dict[str, Any]:
        """Process documents synchronously"""
        
        results = {
            'foreclosure_docs': [],
            'rent_roll': None,
            't12': None,
            'offering_memo': None,
            'property_docs': [],
            'metadata': {
                'files_processed': [],
                'processing_errors': [],
                'async_processing': False
            }
        }
        
        for doc_type, file_path in valid_files.items():
            try:
                if doc_type in ['foreclosure', 'notice', 'deed', 'lien']:
                    result = self._process_foreclosure_document(file_path, doc_type)
                    results['foreclosure_docs'].append(result)
                elif doc_type == 'rent_roll':
                    results['rent_roll'] = self._process_rent_roll(file_path)
                elif doc_type == 't12':
                    results['t12'] = self._process_t12(file_path)
                elif doc_type == 'offering_memo':
                    results['offering_memo'] = self._process_offering_memo(file_path)
                else:
                    result = self._process_generic_property_doc(file_path, doc_type)
                    results['property_docs'].append(result)
                
                results['metadata']['files_processed'].append(doc_type)
                self.logger.info(f"{doc_type} processed successfully")
                
            except Exception as e:
                error_msg = f"Error processing {doc_type}: {str(e)}"
                self.logger.error(error_msg)
                results['metadata']['processing_errors'].append(error_msg)
        
        return results
    
    def _process_foreclosure_document(self, file_path: str, doc_type: str) -> Dict[str, Any]:
        """Process foreclosure-specific documents"""
        
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            extracted_data = self._extract_pdf_content(file_path)
        elif file_ext in ['.xlsx', '.xls', '.xlsb']:
            extracted_data = self._extract_excel_content(file_path)
        else:
            raise ValueError(f"Unsupported file format for {doc_type}: {file_ext}")
        
        # Extract foreclosure-specific information
        foreclosure_data = self._parse_foreclosure_data(extracted_data['text'], doc_type)
        
        return {
            'type': 'foreclosure',
            'subtype': doc_type,
            'format': file_ext[1:],
            'raw_content': extracted_data,
            'foreclosure_data': foreclosure_data,
            'metadata': {
                'file_path': file_path,
                'file_size_mb': os.path.getsize(file_path) / (1024 * 1024),
                'processing_timestamp': datetime.now().isoformat()
            }
        }
    
    def _process_rent_roll(self, file_path: str) -> Dict[str, Any]:
        """Process rent roll document (from multifamily integration)"""
        
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            return self._process_rent_roll_pdf(file_path)
        elif file_ext in ['.xlsx', '.xls', '.xlsb', '.xltx']:
            return self._process_rent_roll_excel(file_path)
        else:
            raise ValueError(f"Unsupported rent roll format: {file_ext}")
    
    def _process_rent_roll_pdf(self, file_path: str) -> Dict[str, Any]:
        """Process PDF rent roll with memory optimization"""
        
        if not PDF_PROCESSING_AVAILABLE:
            raise ValueError("PDF processing libraries not available")
        
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        # Use memory optimization for large files
        if file_size_mb > 10:
            pdf_data = self._process_large_pdf_memory_optimized(file_path)
            text_content = pdf_data['text']
            tables = pdf_data['tables']
        else:
            with pdfplumber.open(file_path) as pdf:
                text_content = ""
                tables = []
                
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
                    
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)
        
        # Parse rent roll data
        units = self._parse_rent_roll_data(text_content, tables)
        
        return {
            'type': 'rent_roll',
            'format': 'pdf',
            'raw_text': text_content,
            'tables': tables,
            'units': units,
            'summary': self._summarize_rent_roll(units),
            'file_size_mb': file_size_mb
        }
    
    def _process_rent_roll_excel(self, file_path: str) -> Dict[str, Any]:
        """Process Excel rent roll"""
        
        if not EXCEL_PROCESSING_AVAILABLE:
            raise ValueError("Excel processing libraries not available")
        
        excel_data = pd.read_excel(file_path, sheet_name=None)
        
        # Find the main rent roll sheet
        rent_roll_sheet = None
        for sheet_name, df in excel_data.items():
            if self._is_rent_roll_sheet(df):
                rent_roll_sheet = df
                break
        
        if rent_roll_sheet is None:
            rent_roll_sheet = list(excel_data.values())[0]
        
        # Parse units data
        units = self._parse_excel_rent_roll(rent_roll_sheet)
        
        return {
            'type': 'rent_roll',
            'format': 'excel',
            'sheets': list(excel_data.keys()),
            'main_sheet': rent_roll_sheet.to_dict('records'),
            'units': units,
            'summary': self._summarize_rent_roll(units)
        }
    
    def _process_t12(self, file_path: str) -> Dict[str, Any]:
        """Process T12 financial statement"""
        
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            return self._process_t12_pdf(file_path)
        elif file_ext in ['.xlsx', '.xls', '.xlsb', '.xltx']:
            return self._process_t12_excel(file_path)
        else:
            raise ValueError(f"Unsupported T12 format: {file_ext}")
    
    def _process_t12_pdf(self, file_path: str) -> Dict[str, Any]:
        """Process PDF T12 statement"""
        
        if not PDF_PROCESSING_AVAILABLE:
            raise ValueError("PDF processing libraries not available")
        
        with pdfplumber.open(file_path) as pdf:
            text_content = ""
            tables = []
            
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n"
                
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)
        
        # Extract financial data
        financial_data = self._parse_t12_text(text_content, tables)
        
        return {
            'type': 't12',
            'format': 'pdf',
            'raw_text': text_content,
            'tables': tables,
            'financial_data': financial_data
        }
    
    def _process_t12_excel(self, file_path: str) -> Dict[str, Any]:
        """Process Excel T12 statement"""
        
        excel_data = pd.read_excel(file_path, sheet_name=None)
        
        # Find financial data sheet
        main_sheet = None
        for sheet_name, df in excel_data.items():
            if self._is_financial_sheet(df):
                main_sheet = df
                break
        
        if main_sheet is None:
            main_sheet = list(excel_data.values())[0]
        
        # Extract financial data
        financial_data = self._parse_t12_data(main_sheet)
        
        return {
            'type': 't12',
            'format': 'excel',
            'sheets': list(excel_data.keys()),
            'financial_data': financial_data,
            'raw_data': main_sheet.to_dict('records')
        }
    
    def _process_offering_memo(self, file_path: str) -> Dict[str, Any]:
        """Process offering memorandum PDF"""
        
        if not PDF_PROCESSING_AVAILABLE:
            raise ValueError("PDF processing libraries not available")
        
        with pdfplumber.open(file_path) as pdf:
            text_content = ""
            tables = []
            
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n"
                
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)
        
        # Extract key information
        property_info = self._extract_property_info(text_content)
        investment_highlights = self._extract_investment_highlights(text_content)
        
        return {
            'type': 'offering_memo',
            'format': 'pdf',
            'raw_text': text_content,
            'tables': tables,
            'property_info': property_info,
            'investment_highlights': investment_highlights
        }
    
    def _process_generic_property_doc(self, file_path: str, doc_type: str) -> Dict[str, Any]:
        """Process generic property document"""
        
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            extracted_data = self._extract_pdf_content(file_path)
        elif file_ext in ['.xlsx', '.xls', '.xlsb']:
            extracted_data = self._extract_excel_content(file_path)
        else:
            extracted_data = {'text': '', 'tables': []}
        
        return {
            'type': 'property_document',
            'subtype': doc_type,
            'format': file_ext[1:],
            'content': extracted_data,
            'metadata': {
                'file_path': file_path,
                'file_size_mb': os.path.getsize(file_path) / (1024 * 1024)
            }
        }
    
    # Financial Analysis Methods
    
    async def _perform_financial_analysis(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive financial analysis"""
        
        financial_analysis = {
            'income_analysis': {},
            'expense_analysis': {},
            'cash_flow_analysis': {},
            'performance_metrics': {}
        }
        
        # Extract financial data from documents
        financial_inputs = self._extract_financial_inputs(document_data)
        
        # Calculate key metrics using FinancialCalculator
        if financial_inputs:
            metrics = self.financial_calculator.calculate_comprehensive_analysis(financial_inputs)
            financial_analysis.update(metrics)
        
        return financial_analysis
    
    async def _calculate_investment_metrics(
        self, 
        document_data: Dict[str, Any], 
        financial_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate investment-specific metrics"""
        
        # Prepare data for investment calculations
        property_data = self._extract_property_data(document_data)
        financial_data = financial_analysis.get('performance_metrics', {})
        
        # Use FinancialCalculator for investment metrics
        investment_metrics = {}
        
        if property_data and financial_data:
            # Calculate IRR, Cap Rate, etc.
            if 'cash_flows' in financial_data:
                investment_metrics['irr'] = self.financial_calculator.calculate_irr(
                    financial_data['cash_flows']
                )
            
            if all(k in financial_data for k in ['noi', 'purchase_price']):
                investment_metrics['cap_rate'] = self.financial_calculator.calculate_cap_rate(
                    financial_data['noi'], 
                    financial_data['purchase_price']
                )
            
            # Calculate viability score
            investment_metrics['viability_score'] = self.financial_calculator.calculate_viability_score({
                **property_data,
                **financial_data
            })
        
        return investment_metrics
    
    async def _perform_ai_analysis(
        self, 
        document_data: Dict[str, Any], 
        financial_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform AI-powered analysis if enabled"""
        
        if not self.ai_enabled:
            return {}
        
        ai_analysis = {}
        
        try:
            # Create comprehensive prompt for AI analysis
            analysis_prompt = self._create_ai_analysis_prompt(document_data, financial_analysis)
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a real estate investment analyst. Provide comprehensive analysis of property investment opportunities."
                    },
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.1
            )
            
            ai_insights = response.choices[0].message.content
            
            ai_analysis = {
                'ai_insights': ai_insights,
                'risk_assessment': self._extract_ai_risk_assessment(ai_insights),
                'recommendations': self._extract_ai_recommendations(ai_insights)
            }
            
        except Exception as e:
            self.logger.error(f"AI analysis failed: {str(e)}")
            ai_analysis = {'error': f"AI analysis failed: {str(e)}"}
        
        return ai_analysis
    
    # Utility and Helper Methods
    
    def validate_file(self, file_path: str) -> Dict[str, Any]:
        """Validate file before processing"""
        
        if not os.path.exists(file_path):
            return {'valid': False, 'error': 'File does not exist'}
        
        try:
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                return {
                    'valid': False,
                    'error': f'File size ({file_size_mb:.1f}MB) exceeds maximum ({self.max_file_size_mb}MB)'
                }
            
            file_ext = Path(file_path).suffix.lower()
            allowed_extensions = ['.pdf', '.xlsx', '.xls', '.xlsb', '.xltx', '.csv']
            if file_ext not in allowed_extensions:
                return {
                    'valid': False,
                    'error': f'File type {file_ext} not supported. Allowed: {allowed_extensions}'
                }
            
            if file_size_mb < 0.001:
                return {'valid': False, 'error': 'File appears to be empty or corrupted'}
            
            return {
                'valid': True,
                'size_mb': file_size_mb,
                'extension': file_ext,
                'readable': os.access(file_path, os.R_OK)
            }
            
        except Exception as e:
            return {'valid': False, 'error': f'Validation error: {str(e)}'}
    
    def _create_property_analysis(self, property_id: str, results: Dict[str, Any]) -> PropertyAnalysis:
        """Create PropertyAnalysis object from processing results"""
        
        # Extract financial metrics
        financial_metrics = FinancialMetrics(
            gross_income=results.get('financial_analysis', {}).get('performance_metrics', {}).get('gross_income', 0),
            noi=results.get('financial_analysis', {}).get('performance_metrics', {}).get('noi', 0),
            cap_rate=results.get('investment_metrics', {}).get('cap_rate', 0),
            cash_on_cash_return=results.get('investment_metrics', {}).get('cash_on_cash_return', 0),
            irr=results.get('investment_metrics', {}).get('irr', 0),
            dscr=results.get('investment_metrics', {}).get('dscr', 0),
            ltv_ratio=results.get('investment_metrics', {}).get('ltv_ratio', 0),
            debt_service=results.get('financial_analysis', {}).get('performance_metrics', {}).get('debt_service', 0),
            cash_flow=results.get('financial_analysis', {}).get('performance_metrics', {}).get('cash_flow', 0),
            equity_multiple=results.get('investment_metrics', {}).get('equity_multiple', 0),
            total_return=results.get('investment_metrics', {}).get('total_return', 0)
        )
        
        return PropertyAnalysis(
            id=f"analysis_{property_id}_{int(time.time())}",
            property_id=property_id,
            analysis_date=datetime.now(),
            financial_metrics=financial_metrics,
            investment_grade=results.get('investment_metrics', {}).get('viability_score', {}).get('grade', 'B'),
            viability_score=results.get('investment_metrics', {}).get('viability_score', {}).get('score', 0.5),
            confidence_score=results.get('confidence_score', 0.8),
            ai_insights=results.get('ai_insights', {}),
            risk_factors=results.get('risk_assessment', {}).get('risk_factors', []),
            opportunities=results.get('recommendations', {}).get('opportunities', []),
            processing_metadata=results.get('metadata', {}),
            document_sources=results['metadata']['files_processed']
        )
    
    def _basic_risk_assessment(self, investment_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Basic rule-based risk assessment when AI is not available"""
        
        risk_score = 0
        risk_factors = []
        
        # Cap rate risk
        cap_rate = investment_metrics.get('cap_rate', 0)
        if cap_rate < 0.04:
            risk_factors.append("Low cap rate indicates higher risk or overpriced property")
            risk_score += 20
        
        # Cash flow risk  
        cash_flow = investment_metrics.get('cash_flow', 0)
        if cash_flow < 0:
            risk_factors.append("Negative cash flow")
            risk_score += 30
        
        # DSCR risk
        dscr = investment_metrics.get('dscr', 1.0)
        if dscr < 1.2:
            risk_factors.append("Debt service coverage ratio below recommended level")
            risk_score += 25
        
        return {
            'risk_score': min(risk_score, 100),
            'risk_level': 'High' if risk_score > 50 else 'Medium' if risk_score > 25 else 'Low',
            'risk_factors': risk_factors
        }
    
    def _basic_recommendations(self, investment_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Basic rule-based recommendations"""
        
        recommendations = []
        opportunities = []
        
        viability_score = investment_metrics.get('viability_score', {}).get('score', 0.5)
        
        if viability_score > 0.7:
            recommendations.append("Strong investment opportunity with good fundamentals")
            opportunities.append("Consider aggressive financing to maximize returns")
        elif viability_score > 0.5:
            recommendations.append("Moderate investment opportunity - review terms carefully")
            opportunities.append("Negotiate purchase price or identify value-add opportunities")
        else:
            recommendations.append("High-risk investment - consider alternative opportunities")
        
        return {
            'recommendations': recommendations,
            'opportunities': opportunities,
            'action_items': ["Conduct property inspection", "Review local market conditions", "Analyze comparable sales"]
        }
    
    # Document parsing helper methods (from multifamily integration)
    
    def _extract_pdf_content(self, file_path: str) -> Dict[str, Any]:
        """Extract content from PDF file"""
        
        if not PDF_PROCESSING_AVAILABLE:
            return {'text': '', 'tables': []}
        
        try:
            with pdfplumber.open(file_path) as pdf:
                text_content = ""
                tables = []
                
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
                    
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)
                
                return {'text': text_content, 'tables': tables}
        except Exception as e:
            self.logger.error(f"Error extracting PDF content: {str(e)}")
            return {'text': '', 'tables': []}
    
    def _extract_excel_content(self, file_path: str) -> Dict[str, Any]:
        """Extract content from Excel file"""
        
        if not EXCEL_PROCESSING_AVAILABLE:
            return {'text': '', 'tables': []}
        
        try:
            excel_data = pd.read_excel(file_path, sheet_name=None)
            
            # Convert all sheets to text representation
            text_parts = []
            for sheet_name, df in excel_data.items():
                text_parts.append(f"Sheet: {sheet_name}")
                text_parts.append(df.to_string())
            
            return {
                'text': '\n'.join(text_parts),
                'tables': [df.values.tolist() for df in excel_data.values()]
            }
        except Exception as e:
            self.logger.error(f"Error extracting Excel content: {str(e)}")
            return {'text': '', 'tables': []}
    
    def _parse_foreclosure_data(self, text: str, doc_type: str) -> Dict[str, Any]:
        """Parse foreclosure-specific data from document text"""
        
        foreclosure_data = {
            'document_type': doc_type,
            'property_address': '',
            'outstanding_debt': 0,
            'foreclosure_date': None,
            'auction_date': None,
            'minimum_bid': 0,
            'plaintiff': '',
            'defendant': '',
            'case_number': ''
        }
        
        # Use regex patterns to extract key information
        patterns = {
            'address': r'(?:property|premises|located at)[\s\S]*?(\d+.*?(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|court|ct|boulevard|blvd)[^,\n]*)',
            'debt': r'(?:amount|sum|debt|balance).*?(?:\$|usd)\s*([\d,]+\.?\d*)',
            'case_number': r'(?:case|docket|file)\s*(?:no|number|#)\s*:?\s*([a-zA-Z0-9-]+)',
            'date': r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            'amount': r'\$\s*([\d,]+\.?\d*)'
        }
        
        try:
            # Extract property address
            address_match = re.search(patterns['address'], text, re.IGNORECASE)
            if address_match:
                foreclosure_data['property_address'] = address_match.group(1).strip()
            
            # Extract debt amount
            debt_match = re.search(patterns['debt'], text, re.IGNORECASE)
            if debt_match:
                debt_str = debt_match.group(1).replace(',', '')
                foreclosure_data['outstanding_debt'] = float(debt_str)
            
            # Extract case number
            case_match = re.search(patterns['case_number'], text, re.IGNORECASE)
            if case_match:
                foreclosure_data['case_number'] = case_match.group(1).strip()
            
            # Extract all monetary amounts for minimum bid estimation
            amounts = re.findall(patterns['amount'], text)
            if amounts:
                amounts_float = [float(amt.replace(',', '')) for amt in amounts]
                foreclosure_data['minimum_bid'] = max(amounts_float) * 0.67  # Typical minimum bid
            
        except Exception as e:
            self.logger.warning(f"Error parsing foreclosure data: {str(e)}")
        
        return foreclosure_data
    
    # Additional helper methods for rent roll and T12 processing
    # (Imported from multifamily document_processor.py)
    
    def _process_large_pdf_memory_optimized(self, file_path: str) -> Dict[str, Any]:
        """Process large PDF files with memory optimization"""
        
        if not PDF_PROCESSING_AVAILABLE:
            raise ValueError("PDF processing libraries not available")
        
        text_chunks = []
        tables = []
        page_count = 0
        
        try:
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text() or ""
                        if page_text.strip():
                            text_chunks.append(page_text)
                        
                        page_tables = page.extract_tables()
                        if page_tables:
                            tables.extend(page_tables)
                        
                        if page_count > 10 and (page_num + 1) % 10 == 0:
                            self.logger.info(f"Processed {page_num + 1}/{page_count} pages")
                    
                    except Exception as e:
                        self.logger.warning(f"Error processing page {page_num + 1}: {e}")
                        continue
            
            # Combine chunks safely
            full_text = '\n'.join(text_chunks)
            
            return {
                'text': full_text,
                'tables': tables,
                'page_count': page_count,
                'chunks_processed': len(text_chunks)
            }
            
        except Exception as e:
            self.logger.error(f"Error in memory-optimized PDF processing: {e}")
            raise
    
    def _parse_rent_roll_data(self, text: str, tables: List[List[List[str]]]) -> List[Dict[str, Any]]:
        """Parse rent roll data from text and tables"""
        
        units = []
        
        # Process tables first (more reliable data)
        for table in tables:
            if len(table) > 1:  # Has header row
                headers = [h.strip().lower() if h else '' for h in table[0]]
                
                # Find key columns
                unit_col = self._find_column_index(headers, ['unit', 'apt', 'apartment', '#'])
                rent_col = self._find_column_index(headers, ['rent', 'current rent', 'monthly rent'])
                sqft_col = self._find_column_index(headers, ['sq ft', 'sqft', 'square feet', 'area'])
                bed_col = self._find_column_index(headers, ['bed', 'beds', 'bedroom', 'br'])
                bath_col = self._find_column_index(headers, ['bath', 'baths', 'bathroom', 'ba'])
                
                for row in table[1:]:
                    if len(row) > max(unit_col or 0, rent_col or 0):
                        unit_data = {
                            'unit': row[unit_col] if unit_col is not None and unit_col < len(row) else '',
                            'current_rent': self._parse_currency(row[rent_col] if rent_col is not None and rent_col < len(row) else ''),
                            'sqft': self._parse_number(row[sqft_col] if sqft_col is not None and sqft_col < len(row) else ''),
                            'bedrooms': self._parse_number(row[bed_col] if bed_col is not None and bed_col < len(row) else ''),
                            'bathrooms': self._parse_number(row[bath_col] if bath_col is not None and bath_col < len(row) else ''),
                            'status': 'occupied'
                        }
                        
                        if unit_data['unit']:
                            units.append(unit_data)
        
        return units
    
    def _parse_excel_rent_roll(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Parse Excel rent roll DataFrame"""
        
        units = []
        
        # Normalize column names
        df.columns = [str(col).strip().lower() for col in df.columns]
        
        # Find key columns
        unit_col = self._find_column_name(df.columns, ['unit', 'apt', 'apartment', '#'])
        rent_col = self._find_column_name(df.columns, ['rent', 'current rent', 'monthly rent'])
        sqft_col = self._find_column_name(df.columns, ['sq ft', 'sqft', 'square feet', 'area'])
        bed_col = self._find_column_name(df.columns, ['bed', 'beds', 'bedroom', 'br'])
        bath_col = self._find_column_name(df.columns, ['bath', 'baths', 'bathroom', 'ba'])
        
        for _, row in df.iterrows():
            unit_data = {
                'unit': str(row[unit_col]) if unit_col and pd.notna(row[unit_col]) else '',
                'current_rent': self._parse_currency(str(row[rent_col])) if rent_col and pd.notna(row[rent_col]) else 0,
                'sqft': self._parse_number(str(row[sqft_col])) if sqft_col and pd.notna(row[sqft_col]) else 0,
                'bedrooms': self._parse_number(str(row[bed_col])) if bed_col and pd.notna(row[bed_col]) else 0,
                'bathrooms': self._parse_number(str(row[bath_col])) if bath_col and pd.notna(row[bath_col]) else 0,
                'status': 'occupied'
            }
            
            if unit_data['unit']:
                units.append(unit_data)
        
        return units
    
    def _parse_t12_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Parse T12 financial data from DataFrame"""
        
        financial_data = {
            'gross_income': 0,
            'operating_expenses': 0,
            'noi': 0,
            'monthly_data': []
        }
        
        # Look for income and expense patterns in the DataFrame
        for _, row in df.iterrows():
            # This would be more sophisticated based on actual T12 format
            pass
        
        return financial_data
    
    def _parse_t12_text(self, text: str, tables: List) -> Dict[str, Any]:
        """Parse T12 data from text content"""
        
        financial_data = {
            'gross_income': 0,
            'operating_expenses': 0,
            'noi': 0
        }
        
        # Use regex to find financial figures
        income_match = re.search(r'gross.*income.*?(\$?[\d,]+)', text, re.IGNORECASE)
        if income_match:
            financial_data['gross_income'] = self._parse_currency(income_match.group(1))
        
        expense_match = re.search(r'(?:operating|total).*expenses?.*?(\$?[\d,]+)', text, re.IGNORECASE)
        if expense_match:
            financial_data['operating_expenses'] = self._parse_currency(expense_match.group(1))
        
        noi_match = re.search(r'(?:noi|net.*operating.*income).*?(\$?[\d,]+)', text, re.IGNORECASE)
        if noi_match:
            financial_data['noi'] = self._parse_currency(noi_match.group(1))
        
        return financial_data
    
    def _extract_property_info(self, text: str) -> Dict[str, Any]:
        """Extract property information from text"""
        
        property_info = {}
        
        # Extract property name
        name_patterns = [
            r'property.*?name.*?:.*?([^\n\r]+)',
            r'([A-Z][a-z]+ [A-Z][a-z]+ (?:Apartments|Complex|Properties))'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                property_info['name'] = match.group(1).strip()
                break
        
        # Extract location
        location_patterns = [
            r'located.*?in.*?([A-Z][a-z]+,? [A-Z]{2})',
            r'address.*?:.*?([^\n]+)'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                property_info['location'] = match.group(1).strip()
                break
        
        return property_info
    
    def _extract_investment_highlights(self, text: str) -> List[str]:
        """Extract investment highlights from text"""
        
        highlights = []
        
        # Look for bullet points or numbered lists
        highlight_patterns = [
            r'[•▪▫]\s*([^\n\r]+)',
            r'\d+\.\s*([^\n\r]+)',
            r'-\s*([^\n\r]+)'
        ]
        
        for pattern in highlight_patterns:
            matches = re.findall(pattern, text)
            highlights.extend([match.strip() for match in matches])
        
        return highlights[:10]  # Limit to top 10
    
    def _summarize_rent_roll(self, units: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize rent roll data"""
        
        if not units:
            return {}
        
        total_units = len(units)
        total_rent = sum(unit.get('current_rent', 0) for unit in units)
        avg_rent = total_rent / total_units if total_units > 0 else 0
        total_sqft = sum(unit.get('sqft', 0) for unit in units)
        avg_sqft = total_sqft / total_units if total_units > 0 else 0
        
        return {
            'total_units': total_units,
            'total_monthly_rent': total_rent,
            'average_rent': avg_rent,
            'total_sqft': total_sqft,
            'average_sqft': avg_sqft,
            'rent_per_sqft': avg_rent / avg_sqft if avg_sqft > 0 else 0
        }
    
    def _is_rent_roll_sheet(self, df: pd.DataFrame) -> bool:
        """Check if DataFrame is a rent roll sheet"""
        
        columns = [str(col).lower() for col in df.columns]
        rent_keywords = ['unit', 'rent', 'sqft', 'bedroom', 'apt']
        return sum(1 for keyword in rent_keywords if any(keyword in col for col in columns)) >= 2
    
    def _is_financial_sheet(self, df: pd.DataFrame) -> bool:
        """Check if DataFrame is a financial sheet"""
        
        columns = [str(col).lower() for col in df.columns]
        financial_keywords = ['income', 'expense', 'revenue', 'noi', 'month']
        return sum(1 for keyword in financial_keywords if any(keyword in col for col in columns)) >= 2
    
    def _find_column_index(self, headers: List[str], keywords: List[str]) -> Optional[int]:
        """Find column index by keywords"""
        
        for i, header in enumerate(headers):
            for keyword in keywords:
                if keyword in header:
                    return i
        return None
    
    def _find_column_name(self, columns: List[str], keywords: List[str]) -> Optional[str]:
        """Find column name by keywords"""
        
        for col in columns:
            for keyword in keywords:
                if keyword in col:
                    return col
        return None
    
    def _parse_currency(self, value: str) -> float:
        """Parse currency string to float"""
        
        if not value or pd.isna(value):
            return 0.0
        
        # Remove currency symbols and commas
        cleaned = re.sub(r'[$,]', '', str(value).strip())
        
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    def _parse_number(self, value: str) -> float:
        """Parse number string to float"""
        
        if not value or pd.isna(value):
            return 0.0
        
        try:
            return float(str(value).strip())
        except ValueError:
            return 0.0
    
    def _extract_financial_inputs(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract financial inputs from processed documents"""
        
        financial_inputs = {}
        
        # Extract from rent roll
        if document_data.get('rent_roll'):
            rent_roll = document_data['rent_roll']
            summary = rent_roll.get('summary', {})
            
            financial_inputs.update({
                'gross_monthly_income': summary.get('total_monthly_rent', 0),
                'total_units': summary.get('total_units', 0),
                'average_rent': summary.get('average_rent', 0),
                'total_sqft': summary.get('total_sqft', 0)
            })
        
        # Extract from T12
        if document_data.get('t12'):
            t12_data = document_data['t12'].get('financial_data', {})
            
            financial_inputs.update({
                'annual_gross_income': t12_data.get('gross_income', 0),
                'annual_operating_expenses': t12_data.get('operating_expenses', 0),
                'noi': t12_data.get('noi', 0)
            })
        
        # Extract from foreclosure docs
        foreclosure_docs = document_data.get('foreclosure_docs', [])
        for doc in foreclosure_docs:
            foreclosure_data = doc.get('foreclosure_data', {})
            if foreclosure_data.get('outstanding_debt'):
                financial_inputs['outstanding_debt'] = foreclosure_data['outstanding_debt']
            if foreclosure_data.get('minimum_bid'):
                financial_inputs['estimated_acquisition_cost'] = foreclosure_data['minimum_bid']
        
        return financial_inputs
    
    def _extract_property_data(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract property data from processed documents"""
        
        property_data = {}
        
        # Extract from offering memo
        if document_data.get('offering_memo'):
            offering_memo = document_data['offering_memo']
            property_info = offering_memo.get('property_info', {})
            
            property_data.update({
                'property_name': property_info.get('name', ''),
                'location': property_info.get('location', ''),
                'property_type': 'multifamily'
            })
        
        # Extract from foreclosure documents
        foreclosure_docs = document_data.get('foreclosure_docs', [])
        for doc in foreclosure_docs:
            foreclosure_data = doc.get('foreclosure_data', {})
            if foreclosure_data.get('property_address'):
                property_data['address'] = foreclosure_data['property_address']
                break
        
        # Extract from rent roll
        if document_data.get('rent_roll'):
            rent_roll = document_data['rent_roll']
            summary = rent_roll.get('summary', {})
            
            property_data.update({
                'total_units': summary.get('total_units', 0),
                'total_sqft': summary.get('total_sqft', 0)
            })
        
        return property_data
    
    def _create_ai_analysis_prompt(self, document_data: Dict[str, Any], financial_analysis: Dict[str, Any]) -> str:
        """Create comprehensive AI analysis prompt"""
        
        prompt_parts = [
            "Analyze this real estate investment opportunity based on the following data:",
            ""
        ]
        
        # Add property information
        property_data = self._extract_property_data(document_data)
        if property_data:
            prompt_parts.append("Property Information:")
            for key, value in property_data.items():
                prompt_parts.append(f"- {key.replace('_', ' ').title()}: {value}")
            prompt_parts.append("")
        
        # Add financial information
        financial_inputs = self._extract_financial_inputs(document_data)
        if financial_inputs:
            prompt_parts.append("Financial Information:")
            for key, value in financial_inputs.items():
                if isinstance(value, (int, float)) and value > 0:
                    prompt_parts.append(f"- {key.replace('_', ' ').title()}: ${value:,.2f}")
            prompt_parts.append("")
        
        # Add analysis request
        prompt_parts.extend([
            "Please provide analysis on:",
            "1. Investment viability and potential returns",
            "2. Key risk factors and mitigation strategies", 
            "3. Market positioning and competitive advantages",
            "4. Specific recommendations for this investment",
            "5. Overall investment grade (A, B, C, D) with rationale",
            "",
            "Format your response with clear sections for each area of analysis."
        ])
        
        return '\n'.join(prompt_parts)
    
    def _extract_ai_risk_assessment(self, ai_insights: str) -> Dict[str, Any]:
        """Extract risk assessment from AI response"""
        
        # Simple extraction - could be more sophisticated
        risk_factors = []
        risk_level = "Medium"
        
        if "high risk" in ai_insights.lower():
            risk_level = "High"
        elif "low risk" in ai_insights.lower():
            risk_level = "Low"
        
        # Extract bullet points that mention risk
        risk_patterns = re.findall(r'[•\-]\s*([^.\n]*risk[^.\n]*)', ai_insights, re.IGNORECASE)
        risk_factors = [factor.strip() for factor in risk_patterns]
        
        return {
            'risk_level': risk_level,
            'risk_factors': risk_factors[:5]  # Limit to top 5
        }
    
    def _extract_ai_recommendations(self, ai_insights: str) -> Dict[str, Any]:
        """Extract recommendations from AI response"""
        
        recommendations = []
        opportunities = []
        
        # Extract recommendations section
        recommendations_match = re.search(r'recommendations?:?\s*(.*?)(?=\n\d+\.|$)', ai_insights, re.IGNORECASE | re.DOTALL)
        if recommendations_match:
            recommendations_text = recommendations_match.group(1)
            recommendations = re.findall(r'[•\-]\s*([^\n]+)', recommendations_text)
        
        # Extract opportunities or action items
        opportunities_patterns = [
            r'opportunities?:?\s*(.*?)(?=\n\d+\.|$)',
            r'actions?:?\s*(.*?)(?=\n\d+\.|$)'
        ]
        
        for pattern in opportunities_patterns:
            match = re.search(pattern, ai_insights, re.IGNORECASE | re.DOTALL)
            if match:
                opportunities_text = match.group(1)
                opportunities = re.findall(r'[•\-]\s*([^\n]+)', opportunities_text)
                break
        
        return {
            'recommendations': [rec.strip() for rec in recommendations],
            'opportunities': [opp.strip() for opp in opportunities]
        }