from typing import Optional

from domain.pro_offerers.paginated_offerers import PaginatedOfferers
from domain.pro_offerers.paginated_offerers_repository import PaginatedOfferersRepository
from models import Offerer, VenueSQLEntity, UserOfferer
from repository.offerer_queries import filter_offerers_with_keywords_string


class PaginatedOfferersSQLRepository(PaginatedOfferersRepository):
    def with_status_and_keywords(self,
                                 user_id: int,
                                 user_is_admin: bool,
                                 page: Optional[int],
                                 pagination_limit: int,
                                 only_validated_offerers: Optional[bool],
                                 is_filtered_by_offerer_status: bool,
                                 keywords: Optional[str] = None) -> PaginatedOfferers:
        query = Offerer.query

        if not user_is_admin:
            query = query \
                .join(UserOfferer, UserOfferer.offererId == Offerer.id) \
                .filter(UserOfferer.userId == user_id)

        if is_filtered_by_offerer_status:
            if only_validated_offerers:
                query = query.filter(Offerer.validationToken == None)
            else:
                query = query.filter(Offerer.validationToken != None)

        if keywords is not None:
            query = query.join(VenueSQLEntity, VenueSQLEntity.managingOffererId == Offerer.id)
            query = filter_offerers_with_keywords_string(query, keywords)

        query = query.order_by(Offerer.name)
        query = query.paginate(page, per_page=int(pagination_limit), error_out=False)
        offerers = query.items

        for offerer in offerers:
                offerer.append_user_has_access_attribute(user_id=user_id, is_admin=user_is_admin)

        total = query.total

        return PaginatedOfferers(offerers, total)
