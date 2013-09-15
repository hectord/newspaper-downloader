%rebase layout title='Authentification', name='NPs', path=path
<form class="form-horizontal" action="" method="POST">
  <div class="form-group {{'has-error' if loginError else ''}}">
    <label class="col-lg-2 control-label" for="username">Login</label>
    <div class="col-lg-4">
      <input type="text" class="form-control" name="username" id="username" value="{{get('username', '')}}" placeholder="Login"/>
      %if loginError:
        <span class="help-block">
          Login/mot de passe invalide
        </span>
      %end  
    </div>
  </div>
  <div class="form-group {{'has-error' if loginError else ''}}">
    <label class="col-lg-2 control-label" for="password">Mot de passe</label>
    <div class="col-lg-4">
      <input type="password" class="form-control" name="password" id="password" placeholder="Mot de passe"/>
    </div>
  </div>
  <div class="control-group">
    <div class="col-lg-offset-2 col-lg-4">
      <button type="submit" class="btn btn-default">Sign in</button>
    </div>
  </div>
</form>

<script language="javascript">
  $(document).ready(function(){
    $('#username').select();
  });
</script>

