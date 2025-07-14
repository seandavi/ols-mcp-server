from pydantic import BaseModel, Field, HttpUrl
from typing import Optional

class OntologyInfo(BaseModel):
    id: str = Field(..., description="Unique identifier for the ontology", alias="ontologyId")
    title: str = Field(..., description="Name of the ontology")
    version: Optional[str] = Field(None, description="Version of the ontology")
    description: Optional[str] = Field(None, description="Description of the ontology")
    domain: Optional[str] = Field(None, description="Domain of the ontology")
    homepage: Optional[HttpUrl] = Field(None, description="URL for the ontology")
    preferred_prefix: Optional[str] = Field(None, description="Preferred prefix for the ontology", alias="preferredPrefix")
    number_of_terms: Optional[int] = Field(None, description="Number of terms in the ontology")
    number_of_classes: Optional[int] = Field(None, description="Number of classes in the ontology", alias="numberOfClasses")
    repository: Optional[HttpUrl] = Field(None, description="Repository URL for the ontology")
    
class PagedResponse(BaseModel):
    total_elements: int = Field(0, description="Total number of items", alias="totalElements")
    page: int = Field(0, description="Current page number")
    size: int = Field(20, description="Starting index of the current page", alias="numElements")
    total_pages: int = Field(0, description="Total number of pages", alias="totalPages")
    
class OntologySearchResponse(PagedResponse):
    ontologies: list[OntologyInfo] = Field(..., description="List of ontologies matching the search criteria")
    

class TermInfo(BaseModel):
    iri: HttpUrl = Field(..., description="IRI of the term")
    ontology_name: str = Field(..., description="Name of the ontology containing the term")
    short_form: str = Field(..., description="Short form identifier for the term")
    label: str = Field(..., description="Human-readable label for the term")
    obo_id: Optional[str] = Field(None, description="OBOLibrary ID for the term", alias="oboId")
    is_obsolete: Optional[bool] = Field(False, description="Indicates if the term is obsolete")

class TermSearchResponse(PagedResponse):
    num_found: int = Field(0, description="Total number of terms found", alias="numFound")
    terms: list[TermInfo] = Field(..., description="List of terms matching the search criteria")
    
class DetailedTermInfo(TermInfo):
    description: Optional[list[str]] = Field(None, description="Definition of the term")
    synonyms: Optional[list[str]] = Field(None, description="List of synonyms for the term")