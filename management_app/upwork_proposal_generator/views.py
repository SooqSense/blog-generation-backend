"""
Django views for Upwork Proposal Generator API.
"""

import logging
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse

from .models import UpworkProposal
from .serializers import (
    UpworkProposalCreateSerializer,
    UpworkProposalResponseSerializer,
    UpworkProposalListSerializer,
    ProposalGenerationStatusSerializer,
    GenerateProposalDirectSerializer,
    UpworkProposalDeleteSerializer,
    UpworkProposalDownloadSerializer,
    ErrorResponseSerializer
)
from .services.agent.agent import upwork_proposal_agent

# Import organization access control
from management_app.authentication.services.access_control import require_organization_access, RequireOrganizationMixin, get_user_selected_organization

logger = logging.getLogger(__name__)


@extend_schema_view(
    get=extend_schema(
        summary="List user's proposals",
        description="Get a list of all proposals created by the authenticated user.",
        responses={200: UpworkProposalListSerializer(many=True)},
        tags=["Upwork Proposals"]
    ),
    post=extend_schema(
        summary="Create new proposal generation request",
        description="Create a new Upwork proposal generation request with client details and requirements. The AI will automatically generate a tailored proposal using relevant project examples from the knowledge base.",
        request=UpworkProposalCreateSerializer,
        responses={
            201: UpworkProposalResponseSerializer,
            400: OpenApiResponse(description='Invalid input data')
        },
        tags=["Upwork Proposals"]
    )
)
class UpworkProposalListCreateView(RequireOrganizationMixin, generics.ListCreateAPIView):
    """List user's proposals and create new proposal generation requests."""
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return proposals for the current user's organization."""
        organization_name = get_user_selected_organization(self.request)
        return UpworkProposal.objects.filter(
            user_id=self.request.user.id,
            organization_name=organization_name
        )
    
    def get_serializer_class(self):
        """Return appropriate serializer based on request method."""
        if self.request.method == 'POST':
            return UpworkProposalCreateSerializer
        return UpworkProposalListSerializer
    
    def perform_create(self, serializer):
        """Create proposal and trigger generation."""
        # Save the proposal with Clerk user data and initial status
        organization_name = get_user_selected_organization(self.request)
        organization_id = getattr(self.request.user, 'organization_id', None)
        proposal = serializer.save(
            user_id=self.request.user.id,
            username=self.request.user.username,
            email=self.request.user.email,
            organization_id=organization_id,
            organization_name=organization_name,
            status='generating'
        )
        
        # Trigger async proposal generation
        try:
            self._generate_proposal_content(proposal)
        except Exception as e:
            logger.error(f"❌ Failed to generate proposal for {proposal.id}: {str(e)}")
            proposal.status = 'failed'
            proposal.error_message = str(e)
            proposal.save()
    
    def _generate_proposal_content(self, proposal):
        """Generate proposal content using the agent."""
        try:
            logger.info(f"🚀 Starting proposal generation for ID: {proposal.id}")
            
            # Generate proposal using the agent
            result = upwork_proposal_agent.generate_proposal(
                client_name=proposal.client_name,
                company_name=proposal.company_name,
                title=proposal.title,
                requirements=proposal.requirements,
                company_websites=proposal.get_website_links(),
                your_name=proposal.your_name,
                upwork_profile_link=proposal.upwork_profile_link,
                contact_information=proposal.contact_information
            )
            
            if result.get('success'):
                proposal.proposal_content = result['proposal']
                proposal.status = 'completed'
                proposal.error_message = None
                logger.info(f"✅ Successfully generated proposal for ID: {proposal.id}")
            else:
                proposal.status = 'failed'
                proposal.error_message = result.get('error', 'Unknown error occurred')
                logger.error(f"❌ Proposal generation failed for ID: {proposal.id}")
            
            proposal.updated_at = timezone.now()
            proposal.save()
            
        except Exception as e:
            proposal.status = 'failed'
            proposal.error_message = str(e)
            proposal.save()
            raise


@extend_schema_view(
    get=extend_schema(
        summary="Get proposal details",
        description="Retrieve detailed information about a specific proposal including generated content.",
        responses={
            200: UpworkProposalResponseSerializer,
            404: OpenApiResponse(description='Proposal not found')
        },
        tags=["Upwork Proposals"]
    ),
    put=extend_schema(
        summary="Update proposal",
        description="Update proposal details. Note: This will not regenerate the proposal content.",
        request=UpworkProposalCreateSerializer,
        responses={
            200: UpworkProposalResponseSerializer,
            404: OpenApiResponse(description='Proposal not found'),
            400: OpenApiResponse(description='Invalid input data')
        },
        tags=["Upwork Proposals"]
    ),
    patch=extend_schema(
        summary="Partially update proposal",
        description="Partially update proposal details. Note: This will not regenerate the proposal content.",
        request=UpworkProposalCreateSerializer,
        responses={
            200: UpworkProposalResponseSerializer,
            404: OpenApiResponse(description='Proposal not found'),
            400: OpenApiResponse(description='Invalid input data')
        },
        tags=["Upwork Proposals"]
    ),
    delete=extend_schema(
        summary="Delete proposal",
        description="Delete a specific proposal permanently.",
        responses={
            204: OpenApiResponse(description='Proposal deleted successfully'),
            404: OpenApiResponse(description='Proposal not found')
        },
        tags=["Upwork Proposals"]
    )
)
class UpworkProposalDetailView(RequireOrganizationMixin, generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific proposal."""
    
    permission_classes = [IsAuthenticated]
    serializer_class = UpworkProposalResponseSerializer
    
    def get_queryset(self):
        """Return proposals for the current user's organization."""
        organization_name = get_user_selected_organization(self.request)
        return UpworkProposal.objects.filter(
            user_id=self.request.user.id,
            organization_name=organization_name
        )


@extend_schema(
    request=GenerateProposalDirectSerializer,
    responses={
        200: OpenApiResponse(
            response=ProposalGenerationStatusSerializer,
            description='Proposal generated successfully'
        ),
        400: OpenApiResponse(description='Invalid input data'),
        500: OpenApiResponse(description='Generation failed')
    },
    summary="Generate Upwork proposal directly",
    description="Generate a tailored Upwork proposal using GPT-4 and relevant project examples from knowledge base. Does not save to database.",
    tags=["Upwork Proposals"]
)
@api_view(['POST'])
@require_organization_access()
def generate_proposal_direct(request):
    """
    Generate proposal directly without saving to database.
    Useful for testing or one-off generations.
    """
    serializer = GenerateProposalDirectSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {
                'success': False,
                'message': 'Invalid input data',
                'errors': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Extract validated data
        validated_data = serializer.validated_data
        
        # Generate proposal using the agent
        result = upwork_proposal_agent.generate_proposal(
            client_name=validated_data['client_name'],
            company_name=validated_data['company_name'],
            title=validated_data['title'],
            requirements=validated_data['requirements'],
            company_websites=validated_data.get('company_website_links', []),
            your_name=validated_data.get('your_name'),
            upwork_profile_link=validated_data.get('upwork_profile_link'),
            contact_information=validated_data.get('contact_information')
        )
        
        if result.get('success'):
            return Response({
                'success': True,
                'message': 'Proposal generated successfully',
                'proposal_content': result['proposal'],
                'metadata': {
                    'projects_found': result.get('projects_found', 0),
                    'model_used': result.get('model_used', 'gpt-4o'),
                    'token_usage': result.get('token_usage', {})
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': 'Failed to generate proposal',
                'error': result.get('error', 'Unknown error')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        logger.error(f"❌ Direct proposal generation failed: {str(e)}")
        return Response({
            'success': False,
            'message': 'An error occurred during proposal generation',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    responses={
        200: OpenApiResponse(
            response=ProposalGenerationStatusSerializer,
            description='Proposal regenerated successfully'
        ),
        404: OpenApiResponse(description='Proposal not found'),
        500: OpenApiResponse(description='Regeneration failed')
    },
    summary="Regenerate existing proposal",
    description="Regenerate proposal content for an existing proposal using updated AI model and knowledge base.",
    tags=["Upwork Proposals"]
)
@api_view(['POST'])
@require_organization_access()
def regenerate_proposal(request, proposal_id):
    """Regenerate proposal content for an existing proposal."""
    try:
        proposal = UpworkProposal.objects.get(id=proposal_id, user_id=request.user.id)
    except UpworkProposal.DoesNotExist:
        return Response(
            {
                'success': False,
                'message': 'Proposal not found'
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Update status and trigger regeneration
    proposal.status = 'generating'
    proposal.error_message = None
    proposal.save()
    
    try:
        # Generate new proposal content
        result = upwork_proposal_agent.generate_proposal(
            client_name=proposal.client_name,
            company_name=proposal.company_name,
            title=proposal.title,
            requirements=proposal.requirements,
            company_websites=proposal.get_website_links(),
            your_name=proposal.your_name,
            upwork_profile_link=proposal.upwork_profile_link,
            contact_information=proposal.contact_information
        )
        
        if result.get('success'):
            proposal.proposal_content = result['proposal']
            proposal.status = 'completed'
            proposal.updated_at = timezone.now()
            proposal.save()
            
            return Response({
                'success': True,
                'message': 'Proposal regenerated successfully',
                'proposal_content': result['proposal'],
                'metadata': {
                    'projects_found': result.get('projects_found', 0),
                    'model_used': result.get('model_used', 'gpt-4o')
                }
            }, status=status.HTTP_200_OK)
        else:
            proposal.status = 'failed'
            proposal.error_message = result.get('error', 'Unknown error')
            proposal.save()
            
            return Response({
                'success': False,
                'message': 'Failed to regenerate proposal',
                'error': result.get('error', 'Unknown error')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        proposal.status = 'failed'
        proposal.error_message = str(e)
        proposal.save()
        
        logger.error(f"❌ Proposal regeneration failed for ID {proposal_id}: {str(e)}")
        return Response({
            'success': False,
            'message': 'An error occurred during proposal regeneration',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    responses={
        200: OpenApiResponse(
            response=ProposalGenerationStatusSerializer,
            description='Proposal status retrieved successfully'
        ),
        404: OpenApiResponse(description='Proposal not found')
    },
    summary="Get proposal status",
    description="Get the current status and content of a proposal generation request.",
    tags=["Upwork Proposals"]
)
@api_view(['GET'])
@require_organization_access()
def proposal_status(request, proposal_id):
    """Get the current status of a proposal generation."""
    try:
        proposal = UpworkProposal.objects.get(id=proposal_id, user_id=request.user.id)
        
        serializer = ProposalGenerationStatusSerializer({
            'success': proposal.status == 'completed',
            'message': f'Proposal is {proposal.status}',
            'proposal_id': proposal.id,
            'status': proposal.status,
            'proposal_content': proposal.proposal_content if proposal.status == 'completed' else None,
            'error': proposal.error_message if proposal.status == 'failed' else None,
            'metadata': {
                'created_at': proposal.created_at.isoformat(),
                'updated_at': proposal.updated_at.isoformat()
            }
        })
        
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except UpworkProposal.DoesNotExist:
        return Response(
            {
                'success': False,
                'message': 'Proposal not found'
            },
            status=status.HTTP_404_NOT_FOUND
        )


# Additional Management Views for Upwork Proposals
@extend_schema(
    responses={
        200: OpenApiResponse(
            response=UpworkProposalListSerializer(many=True),
            description="Upwork proposals retrieved successfully."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Get list of all Upwork proposals for the authenticated user's organization.",
)
@api_view(["GET"])
@require_organization_access()
def list_upwork_proposals_api(request):
    """List all Upwork proposals for the user's organization."""
    try:
        user = request.user
        organization_name = get_user_selected_organization(request)
        
        # Filter by organization
        proposals = UpworkProposal.objects.filter(
            organization_name=organization_name
        ).order_by('-created_at')
        
        serializer = UpworkProposalListSerializer(proposals, many=True)
        
        return Response({
            'success': True,
            'message': f'Retrieved {len(proposals)} Upwork proposals',
            'data': serializer.data,
            'count': len(proposals)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error listing Upwork proposals: {str(e)}")
        return Response({
            'error': 'Failed to retrieve Upwork proposals'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    responses={
        200: OpenApiResponse(
            response=UpworkProposalDeleteSerializer,
            description="Upwork proposals deleted successfully."
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Delete one or more Upwork proposals. Provide proposal_id for single deletion or proposal_ids array for bulk deletion.",
)
@api_view(["DELETE"])
@require_organization_access()
def delete_upwork_proposals_api(request):
    """Delete one or more Upwork proposals."""
    try:
        user = request.user
        organization_name = get_user_selected_organization(request)
        
        # Get proposal IDs from request
        proposal_id = request.data.get('proposal_id')
        proposal_ids = request.data.get('proposal_ids', [])
        
        if proposal_id:
            proposal_ids = [proposal_id]
        elif not proposal_ids:
            return Response({
                'error': 'Either proposal_id or proposal_ids must be provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Filter by organization and delete
        deleted_count = 0
        for proposal_id in proposal_ids:
            try:
                proposal = UpworkProposal.objects.get(
                    id=proposal_id,
                    organization_name=organization_name
                )
                proposal.delete()
                deleted_count += 1
            except UpworkProposal.DoesNotExist:
                continue
        
        return Response({
            'success': True,
            'message': f'Successfully deleted {deleted_count} Upwork proposal(s)',
            'deleted_count': deleted_count
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error deleting Upwork proposals: {str(e)}")
        return Response({
            'error': 'Failed to delete Upwork proposals'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    responses={
        200: OpenApiResponse(
            response=UpworkProposalDownloadSerializer,
            description="Upwork proposal PDF generated successfully."
        ),
        404: OpenApiResponse(
            response=ErrorResponseSerializer, description="Upwork proposal not found."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Generate and download an Upwork proposal as PDF.",
)
@api_view(["GET"])
@require_organization_access()
def download_upwork_proposal_pdf_api(request, proposal_id):
    """Download Upwork proposal as PDF."""
    try:
        user = request.user
        organization_name = get_user_selected_organization(request)
        
        # Get proposal with organization filter
        try:
            proposal = UpworkProposal.objects.get(
                id=proposal_id,
                organization_name=organization_name
            )
        except UpworkProposal.DoesNotExist:
            return Response({
                'error': 'Upwork proposal not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Generate PDF (you'll need to implement PDF generation logic)
        # For now, return a placeholder response
        return Response({
            'success': True,
            'message': 'PDF generation not yet implemented',
            'download_url': None,
            'file_name': f"Upwork_Proposal_{proposal.company_name or 'Unknown'}_{proposal.title[:30]}.pdf"
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error generating PDF for Upwork proposal {proposal_id}: {str(e)}")
        return Response({
            'error': 'Failed to generate PDF'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
