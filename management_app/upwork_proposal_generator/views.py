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
    UpworkProposalDeleteSerializer,
    ErrorResponseSerializer
)
from .services.agent.agent import upwork_proposal_agent

# Import organization access control
from management_app.authentication.services.access_control import require_organization_access, RequireOrganizationMixin, get_user_selected_organization

logger = logging.getLogger(__name__)


@extend_schema(
    request=UpworkProposalCreateSerializer,
    responses={
        201: OpenApiResponse(
            response=UpworkProposalResponseSerializer, description="Proposal created successfully."
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer, description="Bad Request - Invalid input."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Create a new Upwork proposal generation request with client details and requirements. The AI will automatically generate a tailored proposal using relevant project examples from the knowledge base.",
)
@api_view(["POST"])
@require_organization_access()
def create_upwork_proposal_api(request):
    """Create a new Upwork proposal generation request."""
    try:
        # Validate request data using the serializer
        serializer = UpworkProposalCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get organization information
        organization_name = get_user_selected_organization(request)
        organization_id = getattr(request.user, 'organization_id', None)
        
        # Create the proposal (initial record)
        proposal = serializer.save(
            user_id=request.user.id,
            username=request.user.username,
            email=request.user.email,
            organization_id=organization_id,
            organization_name=organization_name,
            status='generating'
        )

        # Synchronous generation: produce content inline and return completed result
        try:
            _generate_proposal_content(proposal)  # updates and saves proposal
        except Exception as e:
            logger.error(f"❌ Proposal generation failed for {proposal.id}: {str(e)}")
            # Ensure proposal reflects failure state
            proposal.refresh_from_db()
            response_serializer = UpworkProposalResponseSerializer(proposal)
            return Response(response_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Reload and return the completed proposal
        proposal.refresh_from_db()
        response_serializer = UpworkProposalResponseSerializer(proposal)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error creating Upwork proposal: {str(e)}")
        return Response({
            'error': 'Failed to create proposal'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    responses={
        200: OpenApiResponse(
            response=UpworkProposalResponseSerializer,
            description="Proposal retrieved successfully."
        ),
        404: OpenApiResponse(
            response=ErrorResponseSerializer, description="Proposal not found."
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer, description="Internal Server Error."
        ),
    },
    description="Get a specific Upwork proposal by ID.",
)
@api_view(["GET"])
@require_organization_access()
def get_upwork_proposal_api(request, proposal_id: int):
    """Get a specific Upwork proposal by ID."""
    try:
        user = request.user
        organization_name = get_user_selected_organization(request)
        
        # Get the proposal
        try:
            proposal = UpworkProposal.objects.get(
                id=proposal_id,
                user_id=user.id,
                organization_name=organization_name
            )
        except UpworkProposal.DoesNotExist:
            return Response({
                'error': 'Proposal not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = UpworkProposalResponseSerializer(proposal)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error retrieving Upwork proposal: {str(e)}")
        return Response({
            'error': 'Failed to retrieve proposal'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _generate_proposal_content(proposal):
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
            contact_information=proposal.contact_information,
            use_knowledge_base=proposal.use_knowledge_base
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


