<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>{{get('title', 'Journaux')}}</title>

    <link rel="stylesheet" href="../static/css/bootstrap.min.css" media="screen">
  </head>
  <body>

    <div class="navbar navbar-default navbar-static-top" role="navigation">
      <div class="container">
        <div class="navbar-header">
          <button type="button" class="navbar-toggle" data-toggle="collapse" data-target=".navbar-ex1-collapse">
            <span class="icon-bar"></span>
            <span class="icon-bar"></span>
            <span class="icon-bar"></span>
          </button>
          <a class="navbar-brand">{{get('name', 'NewsPapers')}}</a>
        </div>
        <div class="collapse navbar-collapse navbar-ex1-collapse">
          <ul class="nav navbar-nav">
            %if path == '/login':
              <li class="active"><a href="#">Authentification</a></li>
            %else:
              <li class="{{'active' if current_newspaper == None else ''}}"><a href="/newspapers/?display={{'images' if display == 'images' else 'list'}}">Tous les journaux</a></li>
              %for newspaper in newspapers:
                <li class="{{'active' if newspaper == current_newspaper else ''}}"><a href="/newspapers/{{newspaper}}?display={{'images' if display == 'images' else 'list'}}">{{newspaper}}</a></li>
              %end
            %end
          </ul>
          <ul class="nav navbar-nav navbar-right">
            %if path != '/login':
              <li class="dropdown">
                <a href="#" class="dropdown-toggle" data-toggle="dropdown">Affichage <b class="caret"></b></a>
                <ul class="dropdown-menu">
                  %if display == 'images':
                    <li><a><strong><span class="glyphicon glyphicon-th"></span> grille d'images</strong></a></li>
                    <li><a href="?display=list&from_np={{current_page}}"><span class="glyphicon glyphicon-th-list"></span> liste</a></li>
                  %else:
                    <li><a href="?display=images&from_np={{current_page}}"><span class="glyphicon glyphicon-th"></span> grille d'images</a></li>
                    <li><a><strong><span class="glyphicon glyphicon-th-list"></span> liste</strong></a></li>
                  %end
                </ul>
              </li>
              <li><a href="/logout">Déconnection</a></li>
            %end
          </ul>
        </div>
      </div>
    </div>

    <div class="container">
      %include
    </div>

    <script src="http://code.jquery.com/jquery.js"></script>
    <script src="../static/js/bootstrap.min.js"></script>

  </body>
</html>
