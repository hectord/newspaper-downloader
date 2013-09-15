%rebase layout path=path, newspapers=newspapers, current_newspaper=current_newspaper, display=display, current_page=current_page

%if display == 'images':
  <div class="container">
    <div class="row">
      %for issue in issues:
        <div style="margin-top:20px;" class="col-sm-6 col-md-3">
          <a href="/issue/{{issue.id()}}" class="thumbnail">
            <img style="width:250px; height:342px;" src="/thumbnail/{{issue.id()}}" alt=""/>
            <div class="caption">
              <h5>{{issue.date().strftime('%d.%m.%Y')}}</h5>
            </div>
          </a>
        </div>
      %end
    </div>
  </div>
%else:
  <div class="table-responsive">
    <table class="table table-hover table-striped">
      <thead>
        <tr>
          <th>Nom</th>
          <th>Titre</th>
          <th>Date</th>
        </tr>
      </thead>
      %for issue in issues:
        <tr>
          <td>{{issue.newspaper()}}</td>
          <td>
            <a href="/issue/{{issue.id()}}">
              {{issue.title()}}
            </a>
          </td>
          <td>{{issue.date().strftime('%d.%m.%Y')}}</td>
        </tr>
      %end
    </table>
  </div>
%end

<div class="row" style="margin-top:10px; margin-bottom:10px">
  <div class="col-sm-6">
    %if other_page_numbers[1] != None:
      <a href="?display={{display}}&from_np={{other_page_numbers[1]}}" class="btn btn-default btn-small">&larr; Plus anciens</a>
    %end
  </div>
  <div class="col-sm-6">
    %if other_page_numbers[0] != None:
      <div class="pull-right">
        <a href="?display={{display}}&from_np={{other_page_numbers[0]}}" class="btn btn-default btn-small">Plus récents &rarr;</a>
      </div>
    %end
  </div>
</div>

